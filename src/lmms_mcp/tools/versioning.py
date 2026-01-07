"""Version control tools for LMMS projects."""

import subprocess
from pathlib import Path
from datetime import datetime

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP):
    """Register version control tools."""

    @mcp.tool()
    def save_project_version(
        path: str,
        message: str = "",
        tag: str | None = None,
    ) -> dict:
        """Save the current project state to git.

        Call this after making changes to preserve state and enable rollback.
        Automatically called by other tools when they modify projects.

        Args:
            path: Path to .mmp or .mmpz project file
            message: Commit message (auto-generated if empty)
            tag: Optional tag name for milestones (e.g., "v1", "drums-done")

        Returns:
            Commit info including hash and message
        """
        project_path = Path(path)
        if not project_path.exists():
            return {"error": f"Project not found: {path}"}

        # Get the project directory (for git operations)
        project_dir = project_path.parent

        # Auto-generate message if not provided
        if not message:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"Auto-save {project_path.name} at {timestamp}"

        try:
            # Add the project file
            subprocess.run(
                ["git", "add", str(project_path)],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            # Check if there are changes to commit
            status = subprocess.run(
                ["git", "status", "--porcelain", str(project_path)],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if not status.stdout.strip():
                return {
                    "status": "no_changes",
                    "message": "No changes to commit",
                    "project": project_path.name,
                }

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message, "--", str(project_path)],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {"error": f"Commit failed: {result.stderr}"}

            # Get the commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            commit_hash = hash_result.stdout.strip()

            response = {
                "status": "committed",
                "hash": commit_hash,
                "message": message,
                "project": project_path.name,
            }

            # Add tag if requested
            if tag:
                tag_result = subprocess.run(
                    ["git", "tag", "-f", tag, "-m", message],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                if tag_result.returncode == 0:
                    response["tag"] = tag
                else:
                    response["tag_error"] = tag_result.stderr

            return response

        except subprocess.CalledProcessError as e:
            return {"error": f"Git operation failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def list_project_versions(
        path: str,
        limit: int = 10,
    ) -> dict:
        """List recent versions (commits) of a project file.

        Args:
            path: Path to .mmp or .mmpz project file
            limit: Maximum number of versions to show (default 10)

        Returns:
            List of recent commits for this project
        """
        project_path = Path(path)
        project_dir = project_path.parent

        try:
            result = subprocess.run(
                [
                    "git", "log",
                    f"-{limit}",
                    "--pretty=format:%h|%s|%cr|%d",
                    "--follow",
                    "--", str(project_path)
                ],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {"error": f"Git log failed: {result.stderr}"}

            versions = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        version = {
                            "hash": parts[0],
                            "message": parts[1],
                            "when": parts[2],
                        }
                        if len(parts) > 3 and parts[3].strip():
                            version["tags"] = parts[3].strip()
                        versions.append(version)

            return {
                "project": project_path.name,
                "versions": versions,
                "count": len(versions),
            }

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def restore_project_version(
        path: str,
        version: str,
    ) -> dict:
        """Restore a project to a previous version.

        Args:
            path: Path to .mmp or .mmpz project file
            version: Commit hash or tag to restore (e.g., "abc123" or "v1")

        Returns:
            Status of the restore operation
        """
        project_path = Path(path)
        project_dir = project_path.parent

        try:
            # First, save current state
            save_result = save_project_version(
                path,
                message=f"Auto-save before restore to {version}"
            )

            # Restore the file from the specified version
            result = subprocess.run(
                ["git", "checkout", version, "--", str(project_path)],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {"error": f"Restore failed: {result.stderr}"}

            return {
                "status": "restored",
                "project": project_path.name,
                "restored_to": version,
                "previous_save": save_result.get("hash", "none"),
            }

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def tag_project_milestone(
        path: str,
        tag: str,
        message: str = "",
    ) -> dict:
        """Tag the current project state as a milestone.

        Use this to mark important points like "drums-complete", "v1", etc.

        Args:
            path: Path to .mmp or .mmpz project file
            tag: Tag name (e.g., "v1", "drums-done", "pre-bass")
            message: Description of this milestone

        Returns:
            Tag info
        """
        project_path = Path(path)
        project_dir = project_path.parent

        if not message:
            message = f"Milestone: {tag}"

        try:
            # First commit any pending changes
            save_result = save_project_version(path, message=f"Milestone: {tag}")

            # Create the tag
            result = subprocess.run(
                ["git", "tag", "-f", tag, "-m", message],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {"error": f"Tag failed: {result.stderr}"}

            return {
                "status": "tagged",
                "tag": tag,
                "message": message,
                "project": project_path.name,
                "commit": save_result.get("hash", "current"),
            }

        except Exception as e:
            return {"error": str(e)}
