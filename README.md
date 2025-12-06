# Mentor

A background daemon that watches your notes as you write, extracts concepts, identifies knowledge gaps, and surfaces thought-provoking questions to guide your learning.

## Philosophy

This is not a quiz tool. It's a **curious mentor** that:

- Observes what you're writing about
- Identifies concepts you've named but not fully explained
- Asks questions that lead you toward deeper understanding
- Sparks curiosity rather than demanding answers

The goal is to make you say "ohh, that's how that works!" repeatedly until you fully understand a concept.

## Installation

```bash
cd mentor
pip install -r requirements.txt
export GEMINI_API_KEY='your-key-here'
```

## Usage

```bash
# Watch a specific note
python main.py ~/notes/my-note.md

# Watch a directory
python main.py ~/notes/
```

## How It Works

1. **File Watcher** monitors your markdown files for changes (debounced)
2. **Analyzer** sends content to Gemini, extracts concepts with scores
3. **State Tracker** maintains concept list, tracks what you've addressed
4. **Mentor** generates curiosity-provoking prompts for knowledge gaps
5. Output currently prints to terminal (Neovim integration planned)

## Concept Scoring

Each concept is scored 0.0–1.0 based on explanation depth:

- **0.0**: Just named ("TCP uses a handshake")
- **0.4**: Partially explained, vague
- **0.6**: Explained but shallow
- **0.8**: Explained with reasoning/why
- **1.0**: Deep understanding with edge cases

## Entropy-Based Prioritization

Gaps are prioritized by "entropy delta":

- **Effort signal**: How much work did you put into explaining it?
- **Complexity signal**: How inherently complex is the concept?
- **Priority** = High complexity + Low effort (you hand-waved something hard)

## Configuration

Environment variables:

- `GEMINI_API_KEY` (required)
- `MENTOR_WATCH_PATH` (optional, default watch location)

Edit `config.py` for:

- `DEBOUNCE_SECONDS`: Wait time after file change (default: 2)
- `ANALYSIS_INTERVAL_SECONDS`: Min time between analyses (default: 30)
- `CONCEPT_SCORE_THRESHOLD`: Below this score = gap (default: 0.6)

## Current Status

**Working:**

- File watcher with debounce (monitors markdown files for changes)
- Concept extraction via Gemini 2.5 Flash
- Scoring system (0.0–1.0 explanation depth)
- Entropy delta calculation (complexity - effort prioritization)
- Gap prioritization algorithm
- Mentor prompt generation (thought-provoking questions)
- State persistence to JSON
- Terminal output
- Directory watching (auto-selects most recent file)
- Google GenAI SDK integration (v1.53.0)

**Not Yet Implemented:**

- Neovim integration (virtual text display)
- Learner profile questionnaire
  - works via a survey (almost like a personality quiz) to adapt suggestions to your goals
- Cross-note awareness
- Streaming responses

See `ROADMAP.md` for full implementation plan.
