from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 1.5

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = _TAG_RE.sub(" ", value)
    return _WHITESPACE_RE.sub(" ", without_tags).strip()


def _extract_authors(raw_authors: list[dict]) -> list[str]:
    authors: list[str] = []
    for author in raw_authors or []:
        given = (author.get("given") or "").strip()
        family = (author.get("family") or "").strip()
        name = f"{given} {family}".strip()
        if not name:
            name = (author.get("name") or "").strip()
        if name:
            authors.append(name)
    return authors


def _extract_date(date_obj: dict | None) -> str:
    if not date_obj:
        return ""
    parts = date_obj.get("date-parts")
    if not parts or not parts[0]:
        return ""
    date_parts = parts[0]
    year = date_parts[0] if len(date_parts) > 0 else None
    month = date_parts[1] if len(date_parts) > 1 else 1
    day = date_parts[2] if len(date_parts) > 2 else 1
    if not year:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_pdf_url(links: list[dict]) -> str:
    for link in links or []:
        content_type = (link.get("content-type") or "").lower()
        if "pdf" in content_type:
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into stable, normalized paper records."""
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []

    for item in items:
        doi = (item.get("DOI") or "").strip()
        titles = item.get("title") or []
        title = _clean_text(titles[0]) if titles else ""
        if not doi or not title:
            continue

        published_obj = (
            item.get("published")
            or item.get("published-print")
            or item.get("published-online")
            or item.get("created")
        )
        published = _extract_date(published_obj)
        updated = _extract_date(item.get("indexed") or item.get("deposited")) or published
        if not published:
            continue

        categories = [str(c) for c in (item.get("subject") or [])]
        container_titles = item.get("container-title") or []

        records.append(
            PaperRecord(
                paper_id=doi.lower(),
                title=title,
                summary=_clean_text(item.get("abstract")),
                authors=_extract_authors(item.get("author") or []),
                categories=categories,
                primary_category=categories[0] if categories else "unknown",
                published=published,
                updated=updated,
                abs_url=item.get("URL") or "",
                pdf_url=_extract_pdf_url(item.get("link") or []),
                comment=_clean_text(container_titles[0]) if container_titles else "",
            )
        )

    return records


def _request_with_retry(params: dict) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(CROSSREF_API_URL, params=params, timeout=30)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
            last_error = requests.HTTPError(
                f"Crossref returned status {response.status_code}", response=response
            )

        if attempt < MAX_ATTEMPTS:
            time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    assert last_error is not None
    raise last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data with retry and persist response and record artifacts."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    payload = _request_with_retry(params)

    raw_response_path = settings.paths.raw_api_response
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    records = parse_crossref_payload(payload)

    raw_records_path = settings.paths.raw_records_json
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.write_text(
        json.dumps([asdict(record) for record in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a persisted raw-record snapshot."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in data]
