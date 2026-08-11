import uuid

import pytest

from app.infrastructure.storage.local_file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


def test_save_writes_inside_document_directory(storage, tmp_path):
    document_id = uuid.uuid4()
    path = storage.save(document_id, "report.pdf", b"content")

    assert (tmp_path / str(document_id) / "report.pdf").read_bytes() == b"content"
    assert path == str(tmp_path / str(document_id) / "report.pdf")


@pytest.mark.parametrize(
    ("malicious_filename", "expected_basename"),
    [
        ("../../../../etc/cron.d/evil", "evil"),
        ("../../evil.sh", "evil.sh"),
        ("../outside.pdf", "outside.pdf"),
        ("/etc/passwd", "passwd"),
    ],
)
def test_save_rejects_path_traversal(storage, tmp_path, malicious_filename, expected_basename):
    document_id = uuid.uuid4()
    path = storage.save(document_id, malicious_filename, b"payload")
    document_dir = tmp_path / str(document_id)

    # The write must land inside the per-document directory, under the
    # sanitized basename only — never at the literal traversal target.
    assert path == str(document_dir / expected_basename)
    assert (document_dir / expected_basename).read_bytes() == b"payload"
    assert not (tmp_path.parent / "evil.sh").exists()
    assert not (tmp_path / "outside.pdf").exists()
    assert not (tmp_path.parent / "etc" / "cron.d" / "evil").exists()


def test_delete_removes_file_and_directory(storage, tmp_path):
    document_id = uuid.uuid4()
    path = storage.save(document_id, "report.pdf", b"content")

    storage.delete(path)

    assert not (tmp_path / str(document_id) / "report.pdf").exists()
    assert not (tmp_path / str(document_id)).exists()


def test_delete_is_safe_when_file_already_gone(storage, tmp_path):
    document_id = uuid.uuid4()
    path = storage.save(document_id, "report.pdf", b"content")
    storage.delete(path)

    storage.delete(path)
