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

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, Form
from groq import Groq

router = APIRouter()

client = Groq()  # reads GROQ_API_KEY from environment, same as classifier_llm.py

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

    Raises 400 if the audio file is empty/unreadable, 502 if Groq's API
    fails - never silently returns an empty transcription, since the
    frontend needs to know if it should ask the worker to try again.
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file received.")

    whisper_language = LANGUAGE_MAP.get(language, "en")

    # Groq's SDK wants a file-like object with a real extension in the name
    # for format detection - write the upload to a temp file first rather
    # than passing the raw UploadFile object directly.
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), f.read()),
                model="whisper-large-v3",
                language=whisper_language,
                response_format="text",
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {type(exc).__name__}: {exc}",
        ) from exc
    finally:
        os.unlink(tmp_path)  # always clean up the temp file

    # Groq's response_format="text" returns a plain string directly.
    text = transcription if isinstance(transcription, str) else str(transcription)

    return {"text": text.strip()}