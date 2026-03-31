"""ComposeService — orchestrates video composition via Remotion render script.

Validates inputs, constructs render props, and invokes the Node.js
render script via subprocess.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from app.storage import StorageService


class ComposeServiceError(Exception):
    """Raised when video composition fails."""


class ComposeService:
    def __init__(self, storage: StorageService | None = None):
        self.storage = storage or StorageService()
        self.remotion_script = Path("remotion/src/render.mjs")

    def build_render_props(
        self,
        audio_path: Path,
        subtitle_content: str,
        title: str = "",
        images: list[str] | None = None,
    ) -> dict:
        """Construct the props dict for the Remotion render script.

        Args:
            audio_path: Path to the audio file (resolved to absolute).
            subtitle_content: Raw SRT text content.
            title: Optional title text overlay.
            images: Optional list of background image paths.

        Returns:
            Dict with audioSrc, subtitleText, backgroundImages, titleText.
        """
        resolved_audio = str(audio_path.resolve())
        return {
            "audioSrc": resolved_audio,
            "subtitleText": subtitle_content,
            "backgroundImages": images or [],
            "titleText": title or "",
        }

    def render(self, props: dict, output_path: Path) -> dict:
        """Invoke the Remotion render script via subprocess.

        Args:
            props: Render props dict (audioSrc, subtitleText, etc.).
            output_path: Where to write the output MP4.

        Returns:
            Dict with success, output_path, stdout, stderr.

        Raises:
            ComposeServiceError: On non-zero exit code.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write props to temp JSON file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(props, f)
            props_file = f.name

        try:
            result = subprocess.run(
                [
                    "node",
                    str(self.remotion_script),
                    "--props",
                    props_file,
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                raise ComposeServiceError(
                    f"Render failed (exit {result.returncode}): {result.stderr}"
                )

            return {
                "success": True,
                "output_path": str(output_path),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            raise ComposeServiceError("Render timed out after 600s")
        finally:
            # Clean up temp props file
            Path(props_file).unlink(missing_ok=True)

    def compose(
        self,
        audio_file_path: Path,
        subtitle_content: str,
        output_path: Path,
        title: str = "",
        images: list[str] | None = None,
    ) -> dict:
        """Full compose pipeline: validate → build props → render.

        Args:
            audio_file_path: Path to audio file.
            subtitle_content: Raw SRT text content.
            output_path: Where to write the output MP4.
            title: Optional title text.
            images: Optional background image paths.

        Returns:
            Dict with success, output_path, stdout, stderr.

        Raises:
            ComposeServiceError: If audio file doesn't exist or render fails.
        """
        if not audio_file_path.exists():
            raise ComposeServiceError(f"Audio file not found: {audio_file_path}")

        props = self.build_render_props(
            audio_path=audio_file_path,
            subtitle_content=subtitle_content,
            title=title,
            images=images,
        )

        return self.render(props=props, output_path=output_path)
