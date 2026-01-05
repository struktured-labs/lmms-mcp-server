"""LMMS CLI wrapper for headless operations."""

import subprocess
import shutil
from pathlib import Path
from typing import Any


class LMMSCli:
    """Wrapper for LMMS command-line interface."""

    def __init__(self, lmms_path: str | None = None):
        """Initialize CLI wrapper.

        Args:
            lmms_path: Path to LMMS executable (auto-detected if None)
        """
        self.lmms_path = lmms_path or self._find_lmms()

    def _find_lmms(self) -> str:
        """Find LMMS executable in PATH or common locations."""
        # Check common project-local locations first
        local_paths = [
            Path(__file__).parent.parent.parent.parent.parent / "lmms-install" / "bin" / "lmms",
            Path.home() / "projects" / "lmms-ai" / "lmms-install" / "bin" / "lmms",
        ]
        for path in local_paths:
            if path.exists():
                return str(path)

        # Fall back to system PATH
        lmms = shutil.which("lmms")
        if lmms is None:
            raise RuntimeError(
                "LMMS not found in PATH. Please install LMMS or specify path."
            )
        return lmms

    def render(
        self,
        project_path: Path,
        output_path: str | None = None,
        format: str = "flac",
        sample_rate: int = 44100,
        bit_depth: int = 16,
    ) -> dict[str, Any]:
        """Render a project to audio file.

        Args:
            project_path: Path to .mmp or .mmpz file
            output_path: Output audio file path (auto-generated if None)
            format: Output format: flac, wav, ogg, mp3
            sample_rate: Sample rate in Hz (default 44100)
            bit_depth: Bit depth for output (default 16)

        Returns:
            Dict with output path and render info
        """
        if output_path is None:
            output_path = str(project_path.with_suffix(f".{format}"))

        cmd = [
            self.lmms_path,
            "-r",  # Render mode
            str(project_path),
            "-o", output_path,
            "-f", format,
            "-s", str(sample_rate),
            "-b", str(bit_depth),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": result.stderr,
                    "command": " ".join(cmd),
                }

            return {
                "status": "success",
                "output_path": output_path,
                "format": format,
                "sample_rate": sample_rate,
                "bit_depth": bit_depth,
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Render timed out after 5 minutes",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def dump(self, project_path: Path) -> str | None:
        """Dump .mmpz to XML using lmms --dump.

        Args:
            project_path: Path to .mmpz file

        Returns:
            XML content as string, or None on error
        """
        if project_path.suffix.lower() != ".mmpz":
            # Already .mmp, just read it
            return project_path.read_text()

        cmd = [self.lmms_path, "--dump", str(project_path)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return None

            return result.stdout

        except Exception:
            return None

    def version(self) -> str | None:
        """Get LMMS version string."""
        try:
            result = subprocess.run(
                [self.lmms_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return None
