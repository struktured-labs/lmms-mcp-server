# LMMS MCP Server Tests

This directory contains the test suite for the LMMS MCP server.

## Running Tests

Run all tests:
```bash
uv run pytest tests/ -v
```

Run specific test file:
```bash
uv run pytest tests/test_tracks.py -v
```

Run with coverage:
```bash
uv run pytest tests/ --cov=lmms_mcp --cov-report=html
```

## Test Organization

- `conftest.py` - Pytest fixtures and test configuration
- `test_project.py` - Project management tests
- `test_tracks.py` - Track operations tests
- `test_patterns.py` - Pattern and note tests
- `test_automation.py` - Automation clip tests

## CI/CD

Tests run automatically on:
- Every push to main
- Every pull request

See `.github/workflows/test.yml` for the CI configuration.

## Writing New Tests

1. Add test functions to the appropriate test file
2. Use the fixtures from `conftest.py` for test data
3. Follow the naming convention: `test_<feature_name>`
4. Run tests locally before committing
