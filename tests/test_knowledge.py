from __future__ import annotations

import pytest

from app.i18n import detect_language, small_talk_kind
from app.services import ingest, netguard, search


def _make_pdf(text: str) -> bytes:
    """Build a tiny valid single-page PDF with one line of text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_extract_pdf():
    assert "Delivery takes 2 days" in ingest.extract_pdf(_make_pdf("Delivery takes 2 days"))
    with pytest.raises(ingest.IngestError):
        ingest.extract_pdf(b"not a pdf")


def test_pdf_upload_endpoint(owner):
    client, ws = owner
    r = client.post(
        f"/api/workspaces/{ws['id']}/documents/pdf",
        files={"file": ("prices.pdf", _make_pdf("Haircut price is 40 GEL"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "pdf"
    ans = client.post(f"/api/workspaces/{ws['id']}/test-chat", json={"text": "haircut price"}).json()
    assert "40 GEL" in ans["text"]


def test_extract_html_strips_chrome():
    html = """<html><head><title>Clinic</title><script>var x=1</script></head>
    <body><nav>Menu Home About</nav><main><h1>Services</h1><p>Dental cleaning costs 80 GEL.</p>
    <a href="/prices#top">Prices</a></main><footer>© 2026</footer></body></html>"""
    title, text, links = ingest.extract_html(html, "https://clinic.ge/")
    assert title == "Clinic"
    assert "Dental cleaning costs 80 GEL." in text
    assert "Menu" not in text and "var x" not in text and "2026" not in text
    assert links == ["https://clinic.ge/prices"]


def test_chunking_respects_size_and_overlap():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(20))
    chunks = ingest.chunk_text(text, max_chars=500, overlap=100)
    assert len(chunks) > 5
    assert all(len(c) <= 520 for c in chunks)
    assert ingest.chunk_text("   ") == []
    long_sentence = "x" * 2500
    assert all(len(c) <= 1000 for c in ingest.chunk_text(long_sentence))


def test_tokenizer_prefix_stemming_georgian():
    tokens = search.tokenize("მიწოდების პირობები და ფასები")
    assert "მიწოდების" in tokens and "მიწოდ*" in tokens
    assert "და" not in tokens
    # "მიწოდება" and "მიწოდების" share a prefix token, so they match each other
    assert set(search.tokenize("მიწოდება")) & set(tokens)


def test_language_detection_and_small_talk():
    assert detect_language("გამარჯობა, რა ღირს?") == "ka"
    assert detect_language("Сколько стоит доставка?") == "ru"
    assert detect_language("How much is delivery?") == "en"
    assert detect_language("123", fallback="en") == "en"
    assert small_talk_kind("Hello!") == "greeting"
    assert small_talk_kind("მადლობა დიდი") == "thanks"
    assert small_talk_kind("How much is delivery to Batumi?") is None


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.com/",
        "http://user:pass@example.com/",
    ],
)
def test_netguard_blocks_unsafe_urls(url):
    with pytest.raises(netguard.UnsafeURLError):
        netguard.validate_url(url)


def test_netguard_allows_private_when_configured():
    assert netguard.validate_url("http://127.0.0.1:8080/x", allow_private=True)
