"""Turn PDFs, web pages, FAQs and plain text into searchable chunks."""

from __future__ import annotations

import io
import logging
import re
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Chunk, Document, Workspace
from app.services import embeddings, search
from app.services.netguard import safe_get

log = logging.getLogger(__name__)

_SENTENCE_RE = re.compile(r"(?<=[.!?։。])\s+")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_SKIP_EXT = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4", ".mp3",
    ".css", ".js", ".ico", ".woff", ".woff2", ".xml", ".json",
)


class IngestError(ValueError):
    pass


def clean_text(text: str) -> str:
    lines = [_WS_RE.sub(" ", line).strip() for line in text.replace("\x00", "").splitlines()]
    out: list[str] = []
    blank = False
    for line in lines:
        if line:
            out.append(line)
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """Split into ~max_chars chunks on paragraph/sentence boundaries with a small overlap."""
    text = clean_text(text)
    if not text:
        return []
    pieces: list[str] = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            pieces.append(para)
            continue
        for sentence in _SENTENCE_RE.split(para):
            sentence = sentence.strip()
            while len(sentence) > max_chars:
                cut = sentence.rfind(" ", 0, max_chars)
                cut = cut if cut > max_chars // 2 else max_chars
                pieces.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if sentence:
                pieces.append(sentence)

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for piece in pieces:
        if current and size + len(piece) + 1 > max_chars:
            chunks.append("\n".join(current))
            tail: list[str] = []
            tail_size = 0
            for prev in reversed(current):
                if tail_size + len(prev) > overlap:
                    break
                tail.insert(0, prev)
                tail_size += len(prev) + 1
            current, size = tail, tail_size
        current.append(piece)
        size += len(piece) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise IngestError("The PDF is password protected") from exc
        pages = [page.extract_text() or "" for page in reader.pages]
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001 - pypdf raises many exception types
        raise IngestError(f"Could not read the PDF: {exc}") from exc
    text = clean_text("\n\n".join(pages))
    if not text:
        raise IngestError("No text found in the PDF (is it a scanned image?)")
    return text


def extract_html(html: str | bytes, base_url: str = "") -> tuple[str, str, list[str]]:
    """Returns (title, text, links)."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href, _ = urldefrag(urljoin(base_url, a["href"]))
        if href.startswith(("http://", "https://")):
            links.append(href)
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "header", "template"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    text = clean_text(root.get_text("\n"))
    return title, text, links


def crawl(start_url: str, max_pages: int, allow_private: bool = False) -> list[tuple[str, str, str]]:
    """Breadth-first crawl of the same host. Returns [(url, title, text)]."""
    host = urlparse(start_url).netloc
    queue: deque[str] = deque([start_url])
    seen: set[str] = {start_url}
    pages: list[tuple[str, str, str]] = []
    attempts = 0
    while queue and len(pages) < max_pages and attempts < max_pages * 3:
        url = queue.popleft()
        attempts += 1
        try:
            final_url, ctype, body = safe_get(url, allow_private=allow_private)
        except Exception as exc:  # noqa: BLE001
            if url == start_url:
                raise IngestError(f"Could not download {url}: {exc}") from exc
            log.info("skip %s: %s", url, exc)
            continue
        if "html" not in ctype and ctype:
            if url == start_url:
                raise IngestError("The URL does not point to an HTML page")
            continue
        title, text, links = extract_html(body, final_url)
        if len(text) >= 80:
            pages.append((final_url, title or final_url, text))
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc != host or link in seen or parsed.path.lower().endswith(_SKIP_EXT):
                continue
            seen.add(link)
            queue.append(link)
    if not pages:
        raise IngestError("No readable text found on this page")
    return pages


def add_document(
    db: Session,
    ws: Workspace,
    settings: Settings,
    *,
    kind: str,
    title: str,
    source: str,
    text: str,
    chunk: bool = True,
) -> Document:
    text = clean_text(text)
    if not text:
        raise IngestError("The document is empty")
    doc = Document(
        workspace_id=ws.id,
        kind=kind,
        title=title[:500] or source[:500] or kind,
        source=source,
        content=text,
        char_count=len(text),
    )
    db.add(doc)
    db.flush()
    pieces = chunk_text(text) if chunk else [text]
    vectors = embeddings.embed_safely(pieces, settings)
    for pos, piece in enumerate(pieces):
        db.add(
            Chunk(
                workspace_id=ws.id,
                document_id=doc.id,
                position=pos,
                content=piece,
                embedding=embeddings.to_bytes(vectors[pos]) if vectors else None,
            )
        )
    ws.kb_version = (ws.kb_version or 0) + 1
    search.invalidate(ws.id)
    return doc


def faq_text(question: str, answer: str) -> str:
    return f"Q: {question.strip()}\nA: {answer.strip()}"
