from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json
from pathlib import Path


@dataclass
class Concept:
    """A single concept extracted from notes."""

    name: str
    score: float  # 0.0 to 1.0, how well it's explained
    effort_signal: str  # "low", "medium", "high"
    complexity_signal: str  # "low", "medium", "high"
    current_coverage: str  # What the notes currently say
    what_would_raise_score: str  # What's missing
    location: str  # Where in the note this concept appears
    last_seen: datetime = field(default_factory=datetime.now)
    times_surfaced: int = 0  # How many times we've prompted about this
    engaged: bool = False  # Did user address it after prompting?

    @property
    def entropy_delta(self) -> str:
        """High entropy delta = low effort on high complexity = priority target."""
        effort_map = {"low": 0, "medium": 1, "high": 2}
        complexity_map = {"low": 0, "medium": 1, "high": 2}

        effort = effort_map.get(self.effort_signal, 1)
        complexity = complexity_map.get(self.complexity_signal, 1)

        delta = complexity - effort

        if delta >= 2:
            return "high"
        elif delta >= 1:
            return "medium"
        else:
            return "low"

    @property
    def priority(self) -> float:
        """Higher = more important to surface. Combines score, entropy, engagement."""
        base = 1.0 - self.score  # Lower score = higher priority

        entropy_boost = {"high": 0.3, "medium": 0.15, "low": 0.0}
        base += entropy_boost.get(self.entropy_delta, 0.0)

        # Reduce priority if we've asked about it many times with no engagement
        if self.times_surfaced > 2 and not self.engaged:
            base *= 0.5

        return base

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "effort_signal": self.effort_signal,
            "complexity_signal": self.complexity_signal,
            "current_coverage": self.current_coverage,
            "what_would_raise_score": self.what_would_raise_score,
            "location": self.location,
            "last_seen": self.last_seen.isoformat(),
            "times_surfaced": self.times_surfaced,
            "engaged": self.engaged,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Concept":
        data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)


@dataclass
class MentorState:
    """Tracks all concepts across the current session."""

    concepts: dict[str, Concept] = field(default_factory=dict)  # name -> Concept
    current_file: Optional[str] = None
    last_analysis: Optional[datetime] = None
    note_snapshots: list[str] = field(default_factory=list)  # Recent versions for diff

    def add_or_update_concept(self, concept: Concept) -> None:
        """Add a new concept or update existing one."""
        existing = self.concepts.get(concept.name)

        if existing:
            # Preserve engagement history
            concept.times_surfaced = existing.times_surfaced
            concept.engaged = existing.engaged or (concept.score > existing.score)

        self.concepts[concept.name] = concept

    def get_top_gaps(self, n: int = 5, threshold: float = None) -> list[Concept]:
        """Return top N concepts by priority that are still gaps."""
        from config import CONCEPT_SCORE_THRESHOLD
        if threshold is None:
            threshold = CONCEPT_SCORE_THRESHOLD
        gaps = [c for c in self.concepts.values() if c.score < threshold]
        return sorted(gaps, key=lambda c: c.priority, reverse=True)[:n]

    def mark_surfaced(self, concept_name: str) -> None:
        """Record that we showed a prompt for this concept."""
        if concept_name in self.concepts:
            self.concepts[concept_name].times_surfaced += 1

    def mark_engaged(self, concept_name: str) -> None:
        """Record that user addressed this concept."""
        if concept_name in self.concepts:
            self.concepts[concept_name].engaged = True

    def save_snapshot(self, content: str, max_snapshots: int = 5) -> None:
        """Save a note snapshot for diffing."""
        self.note_snapshots.append(content)
        if len(self.note_snapshots) > max_snapshots:
            self.note_snapshots.pop(0)

    def get_recent_changes(self) -> Optional[str]:
        """Get what changed since last snapshot."""
        if len(self.note_snapshots) < 2:
            return None

        old = set(self.note_snapshots[-2].split("\n"))
        new = set(self.note_snapshots[-1].split("\n"))

        added = new - old
        return "\n".join(added) if added else None

    def save(self, path: Path) -> None:
        """Persist state to disk."""
        data = {
            "concepts": {k: v.to_dict() for k, v in self.concepts.items()},
            "current_file": self.current_file,
            "last_analysis": self.last_analysis.isoformat()
            if self.last_analysis
            else None,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> "MentorState":
        """Load state from disk."""
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text())
            state = cls()
            state.concepts = {
                k: Concept.from_dict(v) for k, v in data.get("concepts", {}).items()
            }
            state.current_file = data.get("current_file")
            if data.get("last_analysis"):
                state.last_analysis = datetime.fromisoformat(data["last_analysis"])
            return state
        except (json.JSONDecodeError, KeyError):
            return cls()
