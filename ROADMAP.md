---
id: ROADMAP
aliases: []
tags: []
---

# Roadmap

## Vision

A mentor that feels like a curious, knowledgeable friend reading over your shoulder — pointing out interesting threads to pull, connections to make, and gaps to fill. Non-intrusive like Cursor's Tab: appears when useful, disappears when you keep typing.

---

## Phase 1: Core Loop ✅

**Status: Complete**

- [x] File watcher with debounce
- [x] Concept extraction via Gemini
- [x] Scoring system (0.0–1.0)
- [x] Entropy delta calculation (complexity - effort)
- [x] Gap prioritization
- [x] Mentor prompt generation
- [x] State persistence to JSON
- [x] Terminal output

---

## Phase 2: Learner Profile

**Status: Not Started**

Add a questionnaire that shapes how the mentor asks questions.

### Questionnaire Dimensions

1. **Depth Target**: explain | use | build | design
2. **Learning Direction**: top_down | bottom_up | why_first | connection_first
3. **Challenge Tolerance**: low | medium | high | contextual
4. **Tangent Appetite**: focused | brief_detours | follow_energy | map_first
5. **Motivation Pattern**: progress | surprise | relevance | elegance
6. **Guidance Level**: minimal | foothold | guided | adaptive

### Implementation

- [ ] Create `profile.py` with questionnaire logic
- [ ] Store profile in `~/.mentor_profile.json`
- [ ] Pass profile to `generate_mentor_prompt()` in analyzer.py
- [ ] Adjust prompt generation based on profile dimensions

### Profile JSON Structure

```json
{
  "depth_target": "build",
  "learning_direction": "why_first",
  "challenge_tolerance": "medium",
  "tangent_appetite": "brief_detours",
  "motivation": "elegance",
  "guidance_level": "foothold"
}
```

---

## Phase 3: Neovim Integration

**Status: Not Started**

Display mentor prompts as virtual text in Neovim.

### Architecture

```
Daemon (Python)          Neovim (Lua plugin)
     │                         │
     └──── Unix Socket ────────┘
           JSON messages
```

### Daemon Side

- [ ] Add `server.py` — Unix socket server
- [ ] Protocol: newline-delimited JSON
- [ ] Messages: `{"type": "prompt", "text": "...", "concept": "..."}`
- [ ] Handle: `get_prompts`, `dismiss`, `next`, `acknowledge`

### Neovim Side

- [ ] Create `lua/mentor/init.lua`
- [ ] Connect to daemon socket on startup
- [ ] Display prompts as virtual text (extmarks)
- [ ] Keybinds:
  - `<Tab>` or custom: cycle through prompts
  - `<Esc>` or typing: dismiss current prompt
  - Optional: `<CR>` to acknowledge/pin

### Virtual Text Options

1. **End of line**: Dim text after cursor line
2. **Below paragraph**: After blank line
3. **Floating window**: Corner of screen
4. **Gutter**: Sign column indicator, expand on hover

Start with floating window (easiest), iterate to inline.

---

## Phase 4: Smart Context

**Status: Not Started**

Don't send full file every time. Be smarter about context.

### Two-Tier Analysis

- **Fast pass** (every change): Only new/changed content
- **Slow pass** (every few minutes): Full file rebuild

### Implementation

- [ ] Track file snapshots (already in state.py)
- [ ] Compute diffs between snapshots
- [ ] Send diff + concept list to LLM
- [ ] LLM updates/adds concepts incrementally

### Context Window Strategy

```
Current paragraph (full)
+ Recent changes (full)
+ Existing concept list (summary)
+ Learner profile (always)
```

---

## Phase 5: Engagement Tracking

**Status: Not Started**

Learn which prompts the user engages with.

### Signals

- **Engaged**: User wrote content addressing the concept after prompt
- **Ignored**: Prompt dismissed or typed over without addressing
- **Explicit**: User pressed acknowledge key

### Implementation

- [ ] After prompt shown, watch for concept keywords in new content
- [ ] Track `times_surfaced` and `engaged` per concept (already in state.py)
- [ ] Deprioritize repeatedly-ignored concepts
- [ ] Boost concepts user engages with quickly

---

## Phase 6: Cross-Note Awareness

**Status: Not Started**

Know what the user has explained in other notes.

### Options

1. **Embedding-based**: Embed all notes, semantic search
2. **Summary-based**: LLM summarizes each note, store summaries
3. **Link-based**: Follow Obsidian [[links]], build graph

### Features

- [ ] "You explained X well in [[other-note]], link it here?"
- [ ] Don't ask about concepts mastered elsewhere
- [ ] Suggest connections across notes

---

## Phase 7: Adaptive Question Style

**Status: Not Started**

Learn what question formats spark the user's curiosity.

### Question Types

- Socratic: "But why would...?"
- Concrete: "What does X actually look like?"
- Connection: "How does this relate to Y?"
- Challenge: "What happens if...?"
- Fun fact: "Did you know...?"

### Implementation

- [ ] Tag generated prompts with type
- [ ] Track engagement by type
- [ ] Weight prompt generation toward preferred types

---

## Phase 8: Polish

**Status: Not Started**

Production readiness.

- [ ] Proper logging (replace print statements)
- [ ] Error recovery (API failures, file issues)
- [ ] Graceful shutdown
- [ ] Config file support (TOML/YAML)
- [ ] Systemd service file
- [ ] Homebrew formula or pip package

---

## Research Notes

### Cursor's Approach

- Uses speculative decoding for speed (not applicable here)
- Custom fine-tuned models (we use prompted Gemini)
- Entropy-based: automate low-entropy actions (we target high-entropy gaps)
- Ghost text UI: appears inline, disappears on typing

### Key Insight

Cursor asks: "How predictable is the next token?"
Mentor asks: "How predictable is the user's understanding?"

Both use entropy. Different domains.

### Latency Budget

- Cursor: <500ms (autocomplete must feel instant)
- Mentor: 2-3s acceptable (prompts are thoughts, not completions)

---

## Open Questions

1. **Prompt persistence**: Should accepted prompts become margin notes in the file?
2. **Multi-file sessions**: Watch one file or whole vault?
3. **Offline mode**: Cache prompts for offline use?
4. **Export**: Generate "what I learned" summary from session?

---

## Non-Goals

- Quiz/flashcard functionality
- Spaced repetition
- Note formatting/organization
- Auto-completing the user's writing
- Storing/analyzing note content beyond current session
