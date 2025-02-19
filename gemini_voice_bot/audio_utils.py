import speech_recognition as sr
import wave

def record_audio(filename="output.wav", duration=5, sample_rate=16000):
    """Records audio from the microphone and saves it to a WAV file."""
    import sounddevice as sd
    import numpy as np

    print("Recording...")
    try:
        # Record audio using sounddevice
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait for the recording to complete

        print("Finished recording.")

        # Save the recording as a WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes because we're using int16
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
    except Exception as e:
        print(f"Error recording audio: {e}")
        return False  # Indicate failure
    return True  # Indicate success

def transcribe_audio(filename="output.wav"):
    """Transcribes audio from a WAV file to text."""
    r = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = r.record(source)  # Record the entire audio file

    try:
        text = r.recognize_google(audio)  # Use Google Web Speech API
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"
