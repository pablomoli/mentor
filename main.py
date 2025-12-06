#!/usr/bin/env python3
"""
Mentor: A learning companion that watches your notes and asks thought-provoking questions.

Usage:
    python main.py <path_to_note.md>

    # Or watch a directory for the most recently modified file
    python main.py <path_to_notes_directory>

Environment:
    GEMINI_API_KEY - Your Gemini API key (required)
    MENTOR_WATCH_PATH - Default path to watch (optional)
"""

import sys
import time
from pathlib import Path
from datetime import datetime

from config import (
    GEMINI_API_KEY,
    WATCH_PATH,
    MIN_CONTENT_LENGTH,
    STATE_FILE,
    ANALYSIS_INTERVAL_SECONDS,
)
from state import MentorState
from watcher import NoteWatcher
from analyzer import extract_concepts, generate_mentor_prompt


class Mentor:
    """Main application that coordinates watching, analysis, and prompting."""

    def __init__(self, watch_path: Path):
        self.watch_path = watch_path.resolve()
        self.state = MentorState.load(STATE_FILE)
        self.watcher: NoteWatcher | None = None
        self.last_analysis_time: float = 0
        self.pending_analysis: bool = False

    def handle_file_change(self, file_path: Path) -> None:
        """Called when a watched file changes."""
        print(f"\n[mentor] Change detected: {file_path.name}")
        print(f"[mentor] Marking for analysis (pending_analysis = True)")
        self.pending_analysis = True
        self.state.current_file = str(file_path)

        # Read and snapshot the content
        try:
            content = file_path.read_text()
            self.state.save_snapshot(content)

            # Check what changed
            changes = self.state.get_recent_changes()
            if changes:
                print(f"[mentor] New content detected ({len(changes)} chars)")
            else:
                print(f"[mentor] No new content (may be first snapshot)")
        except Exception as e:
            print(f"[mentor] Error reading file: {e}")

    def should_analyze(self) -> bool:
        """Determine if we should run analysis now."""
        if not self.pending_analysis:
            return False

        now = time.time()
        time_since_last = now - self.last_analysis_time
        if time_since_last < ANALYSIS_INTERVAL_SECONDS:
            return False

        return True

    def run_analysis(self) -> None:
        """Run concept extraction and generate prompts."""
        if not self.state.current_file:
            return

        file_path = Path(self.state.current_file)
        if not file_path.exists():
            print(f"[mentor] File not found: {file_path}")
            return

        content = file_path.read_text()

        if len(content) < MIN_CONTENT_LENGTH:
            print(f"[mentor] File too short ({len(content)} chars), skipping analysis")
            return

        print(f"\n[mentor] Analyzing: {file_path.name}")
        print("-" * 50)

        # Extract concepts
        concepts = extract_concepts(content, str(file_path))

        if not concepts:
            print("[mentor] No concepts extracted")
            return

        # Update state
        for concept in concepts:
            self.state.add_or_update_concept(concept)

        self.state.last_analysis = datetime.now()
        self.last_analysis_time = time.time()
        self.pending_analysis = False

        # Display results
        print(f"\n[mentor] Found {len(concepts)} concepts:")
        for c in sorted(concepts, key=lambda x: x.priority, reverse=True):
            entropy = c.entropy_delta
            print(
                f"  • {c.name}: score={c.score:.1f}, effort={c.effort_signal}, "
                f"complexity={c.complexity_signal}, entropy_delta={entropy}"
            )

        # Get top gaps and generate prompts
        gaps = self.state.get_top_gaps(n=3)

        if gaps:
            print(f"\n[mentor] Top gaps to address:")
            for gap in gaps:
                print(f"\n  {gap.name} (score: {gap.score:.1f})")
                print(f"     Coverage: {gap.current_coverage[:100]}...")

                # Generate mentor prompt
                prompt = generate_mentor_prompt(gap)
                print(f"\n     {prompt}")

                # Mark as surfaced
                self.state.mark_surfaced(gap.name)
        else:
            print("\n[mentor] No significant gaps found - nice work!")

        # Save state
        self.state.save(STATE_FILE)
        print("\n" + "-" * 50)

    def run(self) -> None:
        """Main run loop."""
        print("=" * 60)
        print("  MENTOR - Learning Companion")
        print("=" * 60)
        print(f"  Watching: {self.watch_path}")
        print(f"  Analysis interval: {ANALYSIS_INTERVAL_SECONDS}s")
        print(f"  State file: {STATE_FILE}")
        print("=" * 60)
        print("\nEdit your notes. I'll ask questions to guide your learning.\n")

        # Set up watcher
        self.watcher = NoteWatcher(self.watch_path, self.handle_file_change)

        # If watching a file, trigger initial analysis
        if self.watch_path.is_file():
            self.handle_file_change(self.watch_path)
        elif self.watch_path.is_dir():
            # Find most recently modified markdown file in directory
            md_files = list(self.watch_path.glob("*.md")) + list(self.watch_path.glob("*.markdown"))
            if md_files:
                most_recent = max(md_files, key=lambda p: p.stat().st_mtime)
                print(f"[mentor] Found most recent file: {most_recent.name}")
                self.handle_file_change(most_recent)
            else:
                print("[mentor] No markdown files found in directory. Waiting for changes...")

        # Start watching
        self.watcher.start()

        try:
            while True:
                # Check if analysis is due
                if self.should_analyze():
                    self.run_analysis()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n[mentor] Shutting down...")
        finally:
            if self.watcher:
                self.watcher.stop()
            self.state.save(STATE_FILE)
            print("[mentor] State saved. Goodbye!")


def main():
    # Check for API key
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("  export GEMINI_API_KEY='your-key-here'")
        sys.exit(1)

    # Get watch path from args or config
    if len(sys.argv) > 1:
        watch_path = Path(sys.argv[1]).expanduser()
    else:
        watch_path = WATCH_PATH

    # Validate path
    if not watch_path.exists():
        print(f"Error: Path does not exist: {watch_path}")
        sys.exit(1)

    # Run mentor
    mentor = Mentor(watch_path)
    mentor.run()


if __name__ == "__main__":
    main()
