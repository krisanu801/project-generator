import os
from dotenv import load_dotenv

load_dotenv()

# Replace with your actual Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "YOURGEMINIAPIKEY"

# Audio recording parameters
CHUNK = 1024  # Size of each audio chunk
FORMAT = 'paInt16'  # Audio format
CHANNELS = 1  # Number of channels
RATE = 16000  # Sample rate

# Chatbot personality
CHATBOT_PERSONALITY = "You are a funny, sarcastic, and slightly mean chatbot, but you love your work and are very helpful."
