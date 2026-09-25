"""Safe outbound HTTP for user-supplied URLs (website import).

Blocks requests to private/loopback/link-local/metadata addresses (SSRF), re-checks every
redirect hop and caps the response size. Set ALLOW_PRIVATE_URLS=true only on a trusted
self-hosted install that must import pages from an intranet.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 5 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; Docs2ChatBot/0.1; +knowledge-import)"


class UnsafeURLError(ValueError):
    pass


def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host: {host}") from exc
    if not infos:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            return False
    return True


def validate_url(url: str, allow_private: bool = False) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http(s) URLs are allowed")
    if not parsed.hostname:
        raise UnsafeURLError("URL has no host")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with credentials are not allowed")
    if not allow_private and not _host_is_public(parsed.hostname):
        raise UnsafeURLError("This address is not publicly reachable")
    return parsed.geturl()


def safe_get(
    url: str, *, allow_private: bool = False, timeout: float = 15.0, max_bytes: int = MAX_BYTES
) -> tuple[str, str, bytes]:
    """GET a URL following up to 5 validated redirects. Returns (final_url, content_type, body)."""
    current = validate_url(url, allow_private)
    with httpx.Client(
        timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    ) as client:
        for _ in range(6):
            with client.stream("GET", current) as resp:
                if resp.status_code in {301, 302, 303, 307, 308} and resp.headers.get("location"):
                    current = validate_url(urljoin(current, resp.headers["location"]), allow_private)
                    continue
                if resp.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"HTTP {resp.status_code} for {current}", request=resp.request, response=resp
                    )
                body = bytearray()
                for part in resp.iter_bytes():
                    body.extend(part)
                    if len(body) > max_bytes:
                        raise UnsafeURLError("Response is too large")
                return current, resp.headers.get("content-type", ""), bytes(body)
    raise UnsafeURLError("Too many redirects")
