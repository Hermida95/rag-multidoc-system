import io

from pypdf import PdfReader

from app.application.ports.text_extractor import TextExtractor
from app.core.exceptions import DocumentProcessingError
from app.domain.entities.document import DocumentType


class PdfTextExtractor(TextExtractor):
    def supports(self, document_type: DocumentType) -> bool:
        return document_type == DocumentType.PDF

    def extract(self, content: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise DocumentProcessingError(f"Could not read PDF: {exc}") from exc

        pages_text = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(f"[page {page_number}]\n{page_text.strip()}")
        return "\n\n".join(pages_text)


class MarkdownTextExtractor(TextExtractor):
    def supports(self, document_type: DocumentType) -> bool:
        return document_type == DocumentType.MARKDOWN

    def extract(self, content: bytes) -> str:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentProcessingError(
                f"Markdown file is not valid UTF-8 text: {exc}"
            ) from exc
