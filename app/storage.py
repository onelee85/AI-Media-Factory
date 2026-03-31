from pathlib import Path
from app.config import settings


class StorageService:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.storage_root

    def project_dir(self, project_id: str) -> Path:
        path = self.root / "projects" / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def audio_dir(self, project_id: str) -> Path:
        path = self.root / "assets" / "audio" / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def subtitle_dir(self, project_id: str = "default") -> Path:
        path = self.root / "assets" / "subtitles" / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def image_dir(self) -> Path:
        path = self.root / "assets" / "images"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def render_dir(self, project_id: str) -> Path:
        path = self.root / "renders" / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def temp_dir(self, job_id: str) -> Path:
        path = self.root / "temp" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_bytes(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def delete(self, path: Path) -> None:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
