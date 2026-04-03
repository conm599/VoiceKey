import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_to_text.app import VoiceToTextApp


if __name__ == "__main__":
    app = VoiceToTextApp()
    app.run()
