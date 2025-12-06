import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# File Watching
WATCH_PATH = (
    Path.home() / "library/Mobile Documents/iCloud~md~obsidian/Documents/Vault/notes"
)
DEBOUNCE_SECONDS = 2.0
ANALYSIS_INTERVAL_SECONDS = 30.0

# Analysis Settings
MIN_CONTENT_LENGTH = 50  # Don't analyze nearly empty files
CONCEPT_SCORE_THRESHOLD = 0.5  # Below this, concept is considered a gap

# State Persistence
STATE_FILE = Path(__file__).parent / "state.json"
