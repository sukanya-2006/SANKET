"""
transcribe.py — NEW backend endpoint, hand this to your backend dev (M4).

Adds a POST /transcribe endpoint that accepts an audio file upload and
returns transcribed text using Groq's Whisper API (whisper-large-v3).

This does NOT touch classifier.py, aggregate.py, or any existing file's
logic. It's a self-contained addition. Wire it into the app the same way
routes.py is wired into main.py.


WHY WHISPER INSTEAD OF THE BROWSER'S BUILT-IN SPEECH API:
Browser speech recognition (Web Speech API) is trained mostly on clean,
standard English speech and performs poorly on Hindi/Odia and on speakers
who aren't fluent/proficient. Whisper large-v3 has meaningfully better
multilingual accuracy and is still free-tier on Groq, so it's a strict
upgrade for the same cost.
"""

import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, Form
from groq import Groq

log = logging.getLogger(__name__)

router = APIRouter()

# Built on first use, not at import - classifier_llm.py is lazy for the same
# reason. Constructing this at import time meant a missing GROQ_API_KEY raised
# while main.py was including this router, and that handler reports the failure
# as "This usually means python-multipart is missing", sending whoever reads it
# after a package that is already installed.
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq()  # reads GROQ_API_KEY from environment
    return _client


# A recorded safety report is seconds of speech, not megabytes of it. Without a
# ceiling the whole upload lands in memory and then on disk before anything
# looks at it, so any caller can exhaust the box with one request.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024

# Map our frontend's language codes to Whisper's expected language codes.
# Whisper uses ISO-639-1 codes. "auto" lets Whisper detect the language
# itself if the worker didn't pick one / picked "auto".
LANGUAGE_MAP = {
    "en": "en",
    "hi": "hi",
    "or": "or",  # Odia
}


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """
    Accepts an audio file (webm/mp3/wav/m4a - whatever MediaRecorder produces
    in the browser) and returns the transcribed text.

    Request: multipart/form-data with fields:
        audio    - the recorded audio file
        language - one of "en", "hi", "or" (defaults to "en" if not sent)

    Response: {"text": "<transcribed text>"}

    Raises 400 if the audio file is empty/unreadable, 413 if it is larger
    than MAX_UPLOAD_BYTES, 502 if Groq's API fails - never silently returns
    an empty transcription, since the frontend needs to know if it should
    ask the worker to try again.
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file received.")

    whisper_language = LANGUAGE_MAP.get(language, "en")

    # Groq's SDK wants a file-like object with a real extension in the name
    # for format detection - write the upload to a temp file first rather
    # than passing the raw UploadFile object directly.
    suffix = os.path.splitext(audio.filename)[1] or ".webm"

    # Stream the upload to disk a chunk at a time and stop at the first chunk
    # that crosses the cap, so an oversized body is refused partway through
    # instead of being buffered whole and then measured.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        size = 0
        oversized = False

        while True:
            chunk = await audio.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                oversized = True
                break
            tmp.write(chunk)

    # The temp file is closed by now - Windows will not unlink an open one.
    try:
        if oversized:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Audio file is larger than "
                    f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                ),
            )

        if not size:
            raise HTTPException(
                status_code=400, detail="Uploaded audio file is empty."
            )

        with open(tmp_path, "rb") as f:
            transcription = _get_client().audio.transcriptions.create(
                file=(os.path.basename(tmp_path), f.read()),
                model="whisper-large-v3",
                language=whisper_language,
                response_format="text",
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        # This endpoint is unauthenticated and the worker screen alert()s
        # `detail` raw, so the exception text - which can name hosts, keys
        # and account identifiers - stays in the log, and the caller gets a
        # reference that appears in both.
        error_ref = uuid.uuid4().hex[:8]

        log.exception("TRANSCRIPTION FAILED (ref %s)", error_ref)

        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed. Reference {error_ref}.",
        ) from exc
    finally:
        os.unlink(tmp_path)  # always clean up the temp file

    # Groq's response_format="text" returns a plain string directly.
    text = transcription if isinstance(transcription, str) else str(transcription)

    return {"text": text.strip()}