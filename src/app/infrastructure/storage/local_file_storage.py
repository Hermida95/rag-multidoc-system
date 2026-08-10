import uuid
from pathlib import Path


class LocalFileStorage:
    """Filesystem-backed implementation of the FileStorage port.

    Files live under a per-document UUID directory so re-uploaded files
    with the same name never collide.
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, document_id: uuid.UUID, filename: str, content: bytes) -> str:
        document_dir = self._base_dir / str(document_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        file_path = document_dir / filename
        file_path.write_bytes(content)
        return str(file_path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
