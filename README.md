# LMMS MCP Server

MCP (Model Context Protocol) server for AI-powered music production with LMMS.

## Features

- **Project Management**: Create, load, save, and render LMMS projects
- **Track Management**: Add instrument and sample tracks
- **Pattern Editing**: Create patterns, add notes, chords, and scale runs
- **Music Theory**: Built-in chord and scale generators
- **Audio Preview**: Render and describe projects for iterative feedback

## Installation

```bash
# Using uv
uv pip install -e .

# With audio analysis support
uv pip install -e ".[audio]"

# With music theory support
uv pip install -e ".[theory]"

# Everything
uv pip install -e ".[all]"
```

## Usage

### As MCP Server

Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "lmms": {
      "command": "uv",
      "args": ["run", "lmms-mcp"]
    }
  }
}
```

### Example Workflow

```
User: Create a new project at 120 BPM with a synth pad playing C major chords

Claude: [Uses create_project, add_instrument_track, create_pattern, add_chord]
        Created project with pad track. Pattern has C major chord at beat 0.

User: Render a preview so I can hear it

Claude: [Uses render_and_describe]
        Rendered to /path/to/project.flac
        Description: 4-bar pattern with C major chord...

User: Add a bass line following the root notes

Claude: [Uses add_notes to add bass notes]
        Added bass notes: C2 at beat 0, 4, 8...
```

## MCP Tools

### Project
- `create_project` - Create new LMMS project
- `load_project` - Load existing project
- `describe_project` - Get human-readable description
- `render_preview` - Render to audio
- `render_and_describe` - Render + describe (core feedback loop)

### Tracks
- `list_tracks` - List all tracks
- `add_instrument_track` - Add synth track
- `add_sample_track` - Add sample-based track
- `remove_track` - Remove track
- `set_track_volume` / `set_track_pan` - Adjust track settings

### Patterns
- `create_pattern` - Create empty pattern
- `add_notes` - Add individual notes
- `add_chord` - Add chord
- `describe_pattern` - Get pattern contents
- `clear_pattern` - Remove all notes

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src
```

## License

MIT
