"""Pattern model for LMMS tracks."""

from pydantic import BaseModel, Field
from typing import Any

from lmms_mcp.models.note import Note


class Pattern(BaseModel):
    """A pattern containing notes in an LMMS track."""

    id: int = Field(default=0, description="Pattern ID")
    name: str = Field(default="Pattern", description="Pattern name")
    position: int = Field(default=0, ge=0, description="Start position in bars")
    length: int = Field(default=4, gt=0, description="Length in bars")
    notes: list[Note] = Field(default_factory=list, description="Notes in the pattern")

    def add_note(self, note: Note) -> None:
        """Add a note to the pattern."""
        self.notes.append(note)

    def remove_note(self, index: int) -> Note | None:
        """Remove note by index."""
        if 0 <= index < len(self.notes):
            return self.notes.pop(index)
        return None

    def clear(self) -> None:
        """Remove all notes from the pattern."""
        self.notes.clear()

    def describe(self) -> dict[str, Any]:
        """Return a description dict."""
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "length": self.length,
            "note_count": len(self.notes),
        }

    def to_description(self) -> str:
        """Human-readable description of pattern contents."""
        if not self.notes:
            return f"Pattern '{self.name}' at bar {self.position}: empty ({self.length} bars)"

        # Group notes by start time
        by_start: dict[float, list[Note]] = {}
        for note in self.notes:
            if note.start not in by_start:
                by_start[note.start] = []
            by_start[note.start].append(note)

        lines = [f"Pattern '{self.name}' at bar {self.position} ({self.length} bars, {len(self.notes)} notes):"]
        for start in sorted(by_start.keys()):
            notes_at_beat = by_start[start]
            if len(notes_at_beat) == 1:
                note = notes_at_beat[0]
                lines.append(f"  Beat {start}: {note.name} (len: {note.length})")
            else:
                # Multiple notes = chord
                names = [n.name for n in notes_at_beat]
                lines.append(f"  Beat {start}: [{', '.join(names)}] (len: {notes_at_beat[0].length})")

        return "\n".join(lines)
