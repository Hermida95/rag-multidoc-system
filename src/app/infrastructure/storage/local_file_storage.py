import shutil
import uuid
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_FALLBACK_FILENAME = "upload"


class LocalFileStorage:
    """Filesystem-backed implementation of the FileStorage port.

    Files live under a per-document UUID directory so re-uploaded files
    with the same name never collide.
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, document_id: uuid.UUID, filename: str, content: bytes) -> str:
        document_dir = self._base_dir / str(document_id)
        document_dir.mkdir(parents=True, exist_ok=True)

        # `filename` is client-supplied. Path(...).name strips any directory
        # components (including "../"), so the write can never land outside
        # document_dir regardless of what the client sends.
        safe_name = Path(filename).name or _FALLBACK_FILENAME
        file_path = document_dir / safe_name

        # Defense in depth: reject anything that still resolves outside the
        # per-document directory (e.g. a filename that is itself "..").
        if document_dir not in file_path.resolve().parents:
            file_path = document_dir / _FALLBACK_FILENAME

        file_path.write_bytes(content)
        return str(file_path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        path.unlink(missing_ok=True)
        # Best-effort cleanup of the now-empty per-document directory.
        try:
            shutil.rmtree(path.parent)
        except OSError as exc:
            logger.warning("file_cleanup_failed", path=str(path.parent), error=str(exc))
