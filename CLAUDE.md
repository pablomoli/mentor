---
id: CLAUDE
aliases: []
tags: []
---

# CLAUDE.md

## Project Overview

Mentor is a learning companion daemon that watches markdown notes and generates thought-provoking questions to guide the user toward deeper understanding. Think "Cursor Tab, but for learning" — ambient, non-intrusive, appears when useful.

## Architecture

```
User writes in Neovim
       ↓
Daemon watches file (watcher.py)
       ↓
On change (debounced) → extract concepts (analyzer.py)
       ↓
Score concepts, calculate entropy delta (state.py)
       ↓
Generate mentor prompts for top gaps (analyzer.py)
       ↓
Display in Neovim as virtual text (not yet implemented)
```

## Key Files

- `main.py` — Entry point, orchestrates the daemon loop
- `config.py` — Settings, API keys, thresholds
- `state.py` — `Concept` and `MentorState` dataclasses, persistence
- `analyzer.py` — Gemini API calls for concept extraction and prompt generation
- `watcher.py` — File system monitoring with watchdog

## Core Concepts

### Entropy Delta

Priority = complexity - effort. High complexity + low effort = user hand-waved something hard = priority target.

### Concept Scoring

0.0 (just named) → 1.0 (deep understanding). Concepts below 0.6 are "gaps."

### Two-Agent Pattern

1. **Analyst agent**: Extracts concepts, scores them, identifies gaps (structured output)
2. **Mentor agent**: Transforms gaps into curiosity-provoking prompts (creative output)

## Commands

```bash
# Run on a note
python main.py path/to/note.md

# Test file watcher only
python watcher.py path/to/notes/

# Required env
export GEMINI_API_KEY='...'
```

## Code Style

- Python 3.11+
- Type hints everywhere
- Dataclasses for data structures
- No classes where functions suffice
- Print statements for debugging (will add proper logging later)

## Current Limitations

- Terminal output only (no Neovim integration yet)
- No learner profile (prompts are generic)
- Full file sent to LLM each time (no smart chunking)
- No streaming (waits for full response)

## What NOT To Do

- Don't make it a quiz tool (no "what is X?" questions)
- Don't add features that interrupt flow
- Don't store note contents (privacy)
- Don't require user to respond to prompts

## See Also

- `ROADMAP.md` — Full implementation plan with phases
- `README.md` — User-facing documentation
