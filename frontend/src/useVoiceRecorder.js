import { useState, useRef } from 'react';
import { api } from './api';

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
      // Goes through api.transcribe so it uses the same BASE_URL as every other call.
      // This used to post to a hardcoded http://localhost:8000, which the browser blocks
      // as mixed content on the HTTPS deployment - voice only ever worked in dev.
      const data = await api.transcribe(audioBlob, language || 'en');
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