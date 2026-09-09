import { useState, useRef } from 'react';

/**
 * useVoiceRecorder - a hook that handles real microphone recording and
 * sends the audio to the backend /transcribe endpoint for accurate
 * speech-to-text (Groq Whisper), instead of relying on the browser's
 * built-in speech recognition (which is inaccurate for Hindi/Odia and
 * for non-fluent speakers).
 *
 * Usage inside a component:
 *
 *   const { isRecording, isTranscribing, startRecording, stopRecording } =
 *     useVoiceRecorder({ language: 'hi', onTranscribed: (text) => setText(text) });
 *
 *   <button onClick={isRecording ? stopRecording : startRecording}>
 *     {isRecording ? 'Stop' : 'Record'}
 *   </button>
 */
export function useVoiceRecorder({ language, onTranscribed, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // webm is the most widely supported recording format across
      // Chrome/Edge/Firefox on both desktop and Android - Whisper on the
      // backend accepts it directly, no conversion needed.
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop the microphone indicator/permission light once we're done
        streamRef.current?.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendForTranscription(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone access failed:', err);
      onError?.(
        'Could not access the microphone. Please check your browser permissions.'
      );
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendForTranscription = async (audioBlob) => {
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', language || 'en');

      const res = await fetch('http://localhost:8000/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Transcription failed (${res.status})`);
      }

      const data = await res.json();
      onTranscribed?.(data.text);
    } catch (err) {
      console.error('Transcription error:', err);
      onError?.(
        'Could not transcribe your recording. Please try again or type instead.'
      );
    } finally {
      setIsTranscribing(false);
    }
  };

  return { isRecording, isTranscribing, startRecording, stopRecording };
}