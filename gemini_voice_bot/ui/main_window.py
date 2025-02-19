import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QPushButton, QTextEdit, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QCoreApplication
import config
import audio_utils
import google.generativeai as genai
import pyttsx3

class GeminiThread(QThread):
    response_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)  # Signal for errors

    def __init__(self, prompt, personality):
        super().__init__()
        self.prompt = prompt
        self.personality = personality
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    def run(self):
        try:
            # Incorporate personality into the prompt
            full_prompt = f"{self.personality}\nUser: {self.prompt}"
            response = self.model.generate_content(full_prompt)
            self.response_signal.emit(response.text)
        except Exception as e:
            self.error_signal.emit(str(e))  # Emit error signal
            print(f"Gemini API Error: {e}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini Voice Bot")
        self.setGeometry(100, 100, 600, 400)

        self.microphone_path = "ui/assets/microphone.png"
        self.listening_path = "ui/assets/listening.png"

        # Initialize the text-to-speech engine
        self.engine = pyttsx3.init()

        # Attempt to set a female voice
        try:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if voice.gender == 'female':  # Corrected attribute
                    self.engine.setProperty('voice', voice.id)
                    print(f"Using voice: {voice.name}")
                    break
            else:
                print("No female voice found. Using default voice.")
        except Exception as e:
            print(f"Error setting voice: {e}")

        self.engine.setProperty('rate', 200)  # Adjust speaking rate if needed

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.set_microphone_icon()
        main_layout.addWidget(self.image_label)

        # Text area for displaying conversation
        self.conversation_text = QTextEdit()
        self.conversation_text.setReadOnly(True)
        main_layout.addWidget(self.conversation_text)

        # Record button
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.start_recording)
        main_layout.addWidget(self.record_button)

        self.setLayout(main_layout)

    def start_recording(self):
        self.set_listening_icon()
        self.record_button.setEnabled(False)  # Disable the button during recording
        self.conversation_text.append("User: (Recording...)")
        QCoreApplication.processEvents() # Force UI update

        if audio_utils.record_audio():
            self.set_microphone_icon()
            self.record_button.setEnabled(True)  # Enable the button after recording

            transcription = audio_utils.transcribe_audio()
            self.conversation_text.append(f"User: {transcription}")

            self.get_gemini_response(transcription)
        else:
            self.conversation_text.append("Error during recording.")
            self.set_microphone_icon()
            self.record_button.setEnabled(True)  # Enable the button after recording

    def get_gemini_response(self, prompt):
        self.conversation_text.append("Gemini: (Thinking...)")
        QCoreApplication.processEvents()  # Update UI
        self.gemini_thread = GeminiThread(prompt, config.CHATBOT_PERSONALITY)
        self.gemini_thread.response_signal.connect(self.update_gemini_response)
        self.gemini_thread.error_signal.connect(self.handle_gemini_error)  # Connect error signal
        self.gemini_thread.start()

    def update_gemini_response(self, response):
        self.conversation_text.append(f"Gemini: {response}")
        self.conversation_text.ensureCursorVisible()  # Scroll to bottom
        self.speak(response)

    def handle_gemini_error(self, error_message):
        self.conversation_text.append(f"Gemini Error: {error_message}")
        QMessageBox.critical(self, "Gemini API Error", error_message)

    def set_microphone_icon(self):
        self.set_image(self.microphone_path)

    def set_listening_icon(self):
        self.set_image(self.listening_path)

    def set_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                print(f"Error: Could not load image at {image_path}")
                # Try loading from absolute path as a fallback
                import os
                absolute_path = os.path.abspath(image_path)
                pixmap = QPixmap(absolute_path)
                if pixmap.isNull():
                    print(f"Error: Could not load image at absolute path {absolute_path}")
                else:
                   self.image_label.setPixmap(pixmap.scaledToWidth(200))
                   return

            self.image_label.setPixmap(pixmap.scaledToWidth(200))  # Adjust size as needed
        except Exception as e:
            print(f"Error setting image: {e}")
            QMessageBox.critical(self, "Image Error", str(e))

    def speak(self, text):
        """Speaks the given text using text-to-speech."""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error during text-to-speech: {e}")
