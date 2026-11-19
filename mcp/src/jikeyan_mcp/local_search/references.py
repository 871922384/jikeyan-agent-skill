"""Offline-testable reference metadata comparison and public database verification.

Comparison and BibTeX parsing adapted from Rex's litflow reference scripts.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from html import unescape
import json
import re
import time
import threading
import unicodedata
from typing import Any, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

@dataclass(frozen=True)
class BibEntry:
    key: str
    entry_type: str
    fields: dict[str, str]


ENTRY_START = re.compile(r"@([A-Za-z]+)\s*([({])", re.MULTILINE)
FIELD_START = re.compile(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*")

def _balanced_end(text: str, start: int, opener: str, closer: str) -> int:
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced BibTeX entry")


def _top_level_comma(text: str) -> int:
    brace_depth = 0
    paren_depth = 0
    quoted = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        elif not quoted:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "," and brace_depth == 0 and paren_depth == 0:
                return index
    return -1


def _strip_bib_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and (
        (value[0] == "{" and value[-1] == "}")
        or (value[0] == '"' and value[-1] == '"')
    ):
        return value[1:-1].strip()
    return value


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    position = 0
    while position < len(text):
        while position < len(text) and text[position] in " \t\r\n,":
            position += 1
        match = FIELD_START.match(text, position)
        if match is None:
            break
        name = match.group(1).lower()
        value_start = match.end()
        comma = _top_level_comma(text[value_start:])
        if comma < 0:
            raw_value = text[value_start:]
            position = len(text)
        else:
            raw_value = text[value_start : value_start + comma]
            position = value_start + comma + 1
        fields[name] = _strip_bib_value(raw_value)
    return fields


def parse_bibtex(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    position = 0
    while True:
        match = ENTRY_START.search(text, position)
        if match is None:
            return entries
        entry_type = match.group(1).lower()
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        content_start = match.end()
        content_end = _balanced_end(text, match.end() - 1, opener, closer)
        content = text[content_start:content_end]
        if entry_type in {"string", "comment", "preamble"}:
            position = content_end + 1
            continue
        comma = _top_level_comma(content)
        if comma < 0:
            raise ValueError(f"BibTeX entry missing field separator near {match.start()}")
        key = content[:comma].strip()
        if not key:
            raise ValueError(f"BibTeX entry missing key near {match.start()}")
        entries.append(BibEntry(key, entry_type, _parse_fields(content[comma + 1 :])))
        position = content_end + 1


def normalize_doi(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi:\s*", "", normalized)
    return normalized.rstrip(". ")


def find_duplicate_keys(entries: Sequence[BibEntry]) -> tuple[str, ...]:
    counts = Counter(entry.key for entry in entries)
    return tuple(sorted(key for key, count in counts.items() if count > 1))


def find_duplicate_dois(entries: Sequence[BibEntry]) -> tuple[str, ...]:
    dois = [normalize_doi(entry.fields["doi"]) for entry in entries if entry.fields.get("doi")]
    counts = Counter(doi for doi in dois if doi)
    return tuple(sorted(doi for doi, count in counts.items() if count > 1))


@dataclass(frozen=True)
class ReferenceVerdict:
    key: str
    status: str
    identifier: str
    differing_fields: tuple[str, ...]
    evidence_source: str
    message: str
    lookup_failed: bool = False


def _plain(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _normalized(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", unescape(_plain(value)).casefold())
    folded = "".join(
        "i" if character == "ı" else character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[^\W_]+", folded, flags=re.UNICODE))


def _year_from_date_parts(value: Any) -> str:
    if isinstance(value, Mapping):
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            return str(parts[0][0])
    return ""


def _years_from_resolved(resolved: Mapping[str, Any]) -> frozenset[str]:
    years = {
        year
        for field in (
            "issued",
            "published-print",
            "published-online",
            "published",
        )
        if (year := _year_from_date_parts(resolved.get(field)))
    }
    text = " ".join(
        _plain(resolved.get(field)) for field in ("year", "pubdate")
    )
    years.update(re.findall(r"\b(?:19|20)\d{2}\b", text))
    return frozenset(years)


def _year_from_resolved(resolved: Mapping[str, Any]) -> str:
    years = _years_from_resolved(resolved)
    if not years:
        return ""
    return sorted(years)[0]


def _surname_key(value: Any) -> str:
    normalized = _normalized(value)
    return normalized.split(" ")[-1] if normalized else ""


def _name_surname(value: Any) -> str:
    normalized = _normalized(value)
    words = normalized.split()
    if not words:
        return ""
    while len(words) > 1 and words[-1] in {"jr", "sr", "ii", "iii", "iv", "2nd", "3rd", "4th"}:
        words.pop()
    if len(words) > 1 and len(words[-1]) <= 4 and words[-1].isalpha():
        return words[-2]
    return words[-1]


def _journal_equivalent(left: str, right: str) -> bool:
    if left == right:
        return True
    stopwords = {"and", "of", "the", "in", "for"}
    left_words = [word for word in left.split() if word not in stopwords]
    right_words = [word for word in right.split() if word not in stopwords]
    if not left_words or not right_words:
        return False
    shortest = min(len(left_words), len(right_words))
    return all(
        first.startswith(second) or second.startswith(first)
        for first, second in zip(left_words[:shortest], right_words[:shortest])
    )


def _title_equivalent(left: str, right: str) -> bool:
    if left == right:
        return True
    compact_left = left.replace(" ", "")
    compact_right = right.replace(" ", "")
    shorter, longer = sorted((compact_left, compact_right), key=len)
    return (
        len(shorter) >= 12
        and len(shorter) / len(longer) >= 0.7
        and longer.startswith(shorter)
    )


def _contains_han(value: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in value)


def _author_scripts_comparable(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    left_text = "".join(left)
    right_text = "".join(right)
    return _contains_han(left_text) == _contains_han(right_text)


def _pages_equivalent(left: str, right: str) -> bool:
    if left == right:
        return True
    left_start = left.split(" ", maxsplit=1)[0]
    right_start = right.split(" ", maxsplit=1)[0]
    return bool(left_start and left_start == right_start)


def _author_surnames(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        surnames: list[str] = []
        for author in value:
            if isinstance(author, Mapping):
                family = author.get("family")
                if family:
                    surnames.append(_surname_key(family))
                    continue
                name = _name_surname(author.get("name"))
            else:
                name = _name_surname(author)
            if name:
                surnames.append(name)
        return tuple(surnames)

    surnames = []
    for author in re.split(r"\s+and\s+", _plain(value), flags=re.IGNORECASE):
        author = author.strip()
        if author.lower() in {"others", "et al", "et al."}:
            break
        if not author:
            continue
        if "," in author:
            surname = author.split(",", maxsplit=1)[0]
        else:
            surname = _name_surname(author)
        normalized = _surname_key(surname)
        if normalized:
            surnames.append(normalized)
    return tuple(surnames)


def _first_author_surname(value: Any) -> str:
    surnames = _author_surnames(value)
    return surnames[0] if surnames else ""


def _resolved_doi(resolved: Mapping[str, Any]) -> str:
    direct = resolved.get("DOI") or resolved.get("doi")
    if direct:
        return normalize_doi(_plain(direct))
    match = re.search(r"10\.\d{4,9}/\S+", _plain(resolved.get("elocationid")), re.IGNORECASE)
    return normalize_doi(match.group(0)) if match else ""


def compare_metadata(
    submitted: BibEntry, resolved: Mapping[str, Any]
) -> ReferenceVerdict:
    differences: list[str] = []
    submitted_fields = submitted.fields
    submitted_title = _normalized(submitted_fields.get("title"))
    resolved_title = _normalized(resolved.get("title"))
    if submitted_title and not _title_equivalent(submitted_title, resolved_title):
        differences.append("title")

    submitted_authors = _author_surnames(submitted_fields.get("author"))
    resolved_authors = _author_surnames(
        resolved.get("author") or resolved.get("authors")
    )
    if (
        submitted_authors
        and resolved_authors
        and _author_scripts_comparable(submitted_authors, resolved_authors)
        and submitted_authors != resolved_authors[: len(submitted_authors)]
    ):
        differences.append("author")

    submitted_year = submitted_fields.get("year", "").strip()
    resolved_years = _years_from_resolved(resolved)
    if submitted_year and resolved_years and submitted_year not in resolved_years:
        if not submitted_year.isdigit() or not any(
            abs(int(submitted_year) - int(year)) == 1 for year in resolved_years
        ):
            differences.append("year")

    submitted_journal = _normalized(submitted_fields.get("journal"))
    resolved_journal = _normalized(
        resolved.get("container-title")
        or resolved.get("fulljournalname")
        or resolved.get("source")
    )
    if (
        submitted_journal
        and resolved_journal
        and not _journal_equivalent(submitted_journal, resolved_journal)
    ):
        differences.append("journal")

    submitted_volume = _normalized(submitted_fields.get("volume"))
    submitted_volume = re.sub(r"^(?:volume|vol)\s+", "", submitted_volume)
    resolved_volume = re.sub(r"^(?:volume|vol)\s+", "", _normalized(resolved.get("volume")))
    if resolved_volume and set(resolved_volume) == {"0"}:
        resolved_volume = ""

    comparisons = {
        "volume": (submitted_volume, resolved_volume),
        "issue": (
            _normalized(submitted_fields.get("issue")),
            _normalized(resolved.get("issue")),
        ),
        "doi": (
            normalize_doi(submitted_fields.get("doi", "")),
            _resolved_doi(resolved),
        ),
    }
    for field, (left, right) in comparisons.items():
        if left and right and left != right:
            differences.append(field)
    submitted_pages = _normalized(
        submitted_fields.get("pages") or submitted_fields.get("page")
    )
    resolved_pages = _normalized(resolved.get("page") or resolved.get("pages"))
    if (
        submitted_pages
        and resolved_pages
        and not _pages_equivalent(submitted_pages, resolved_pages)
    ):
        differences.append("pages")
    identifier = _resolved_doi(resolved)
    return ReferenceVerdict(
        key=submitted.key,
        status="MISMATCH" if differences else "REAL",
        identifier=identifier,
        differing_fields=tuple(differences),
        evidence_source="resolved_metadata",
        message="metadata differs" if differences else "resolved metadata matches",
    )


def _unresolved(entry: BibEntry, source: str, error: Exception | str) -> ReferenceVerdict:
    return ReferenceVerdict(
        entry.key,
        "UNRESOLVED",
        "",
        (),
        source,
        str(error),
    )


class NotFoundError(Exception):
    def __init__(self, status: int = 404):
        self.status = status
        super().__init__("Metadata record not found")


def lookup_error_category(error: Exception) -> str:
    if isinstance(error, HTTPError) and error.code == 429:
        category = "被限流"
    elif isinstance(error, HTTPError) and 500 <= error.code <= 599:
        category = "服务暂不可用"
    elif isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
        category = "响应格式错误"
    else:
        category = "网络错误/超时"
    return category


def _lookup_failure(entry: BibEntry, source: str, error: Exception) -> ReferenceVerdict:
    return ReferenceVerdict(
        entry.key, "UNRESOLVED", "", (), source, f"查询失败：{lookup_error_category(error)}", True
    )


class HttpClient(Protocol):
    def get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> object: ...


_RATE_LOCK = threading.Lock()
_RATE_NEXT: dict[str, float] = {}


class UrlLibHttpClient:
    """Bounded retries and separate, process-local request pacing for each service."""

    def __init__(
        self, *, contact_email='', ncbi_api_key='', retries=3, timeout=20,
        clock=time.monotonic, sleep=time.sleep, opener=urlopen,
    ):
        self.email = contact_email
        self.key = ncbi_api_key
        self.retries = max(1, retries)
        self.timeout = timeout
        self.clock = clock
        self.sleep = sleep
        self.opener = opener
        self.max_requests = None
        self.request_count = 0
        self.next_request = _RATE_NEXT if clock is time.monotonic else {}
        self.rate_lock = _RATE_LOCK if clock is time.monotonic else threading.Lock()

    def get_json(self, url, *, params=None, headers=None):
        host = urlparse(url).hostname
        if host not in ('api.crossref.org', 'eutils.ncbi.nlm.nih.gov', 'clinicaltrials.gov'):
            raise ValueError('unsupported metadata host')
        crossref = host == 'api.crossref.org'
        args = dict(params or {})
        if crossref and self.email:
            args['mailto'] = self.email
        if host == 'eutils.ncbi.nlm.nih.gov':
            args['tool'] = 'jikeyan-mcp'
            if self.email:
                args['email'] = self.email
            if self.key:
                args['api_key'] = self.key
        rate = 3 if host == 'clinicaltrials.gov' else (2 if not self.email else (3 if crossref or not self.key else 8))
        target = url + ('?' + urlencode(args) if args else '')
        ua = 'Jikeyan-MCP/1.0' + (f' (mailto:{self.email})' if self.email else '')
        request = Request(target, headers={
            'User-Agent': ua, 'Accept': 'application/json', **(headers or {}),
        })
        for attempt in range(self.retries):
            if self.max_requests is not None and self.request_count >= self.max_requests:
                raise TimeoutError('request budget exhausted')
            with self.rate_lock:
                wait = self.next_request.get(host, 0) - self.clock()
                if wait > 0:
                    self.sleep(wait)
                self.next_request[host] = self.clock() + 1 / rate
            try:
                self.request_count += 1
                with self.opener(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode('utf-8'))
            except HTTPError as error:
                if error.code == 404:
                    raise NotFoundError() from error
                if error.code != 429 and not 500 <= error.code <= 599:
                    raise
                if attempt + 1 == self.retries:
                    raise
                delay = min(30.0, 0.5 * 2 ** attempt)
                retry = error.headers.get('Retry-After') if error.headers else None
                if retry:
                    try:
                        delay = max(0, min(30.0, float(retry)))
                    except ValueError:
                        try:
                            seconds = (parsedate_to_datetime(retry) - datetime.now(timezone.utc))
                            delay = max(0, min(30.0, seconds.total_seconds()))
                        except (ValueError, TypeError, OverflowError):
                            pass
                self.sleep(delay)
            except (TimeoutError, URLError):
                if attempt + 1 == self.retries:
                    raise
                self.sleep(min(30.0, 0.5 * 2 ** attempt))


def _track_result(entry, metadata, identifier, source):
    verdict = compare_metadata(entry, metadata)
    return ReferenceVerdict(
        verdict.key, verdict.status, identifier, verdict.differing_fields, source, verdict.message
    )


def verify_crossref_track(entry: BibEntry, http: HttpClient) -> ReferenceVerdict:
    doi = normalize_doi(entry.fields.get('doi', ''))
    try:
        if doi:
            data = http.get_json('https://api.crossref.org/works/' + quote(doi, safe='/'))
            metadata = data.get('message') if isinstance(data, Mapping) else None
        else:
            title = entry.fields.get('title', '')
            if not title:
                return _unresolved(entry, 'crossref', 'No title or DOI')
            data = http.get_json(
                'https://api.crossref.org/works', params={'query.title': title, 'rows': '5'}
            )
            message = data.get('message', {}) if isinstance(data, Mapping) else {}
            items = message.get('items', []) if isinstance(message, Mapping) else []
            metadata = next(
                (item for item in items if isinstance(item, Mapping) and item.get('DOI')
                 and _normalized(item.get('title')) == _normalized(title)),
                None,
            )
        if not isinstance(metadata, Mapping):
            return _unresolved(entry, 'crossref', 'No matching record')
        return _track_result(entry, metadata, _resolved_doi(metadata), 'crossref')
    except NotFoundError as error:
        if doi:
            return ReferenceVerdict(
                entry.key, 'MISMATCH', doi, ('doi',), 'crossref', 'DOI 在 Crossref 中不存在'
            )
        return _lookup_failure(entry, 'crossref', error)
    except Exception as error:
        return _lookup_failure(entry, 'crossref', error)


def verify_pubmed_track(entry: BibEntry, http: HttpClient) -> ReferenceVerdict:
    try:
        pmid = entry.fields.get('pmid', '').strip()
        if pmid:
            ids = [pmid]
        else:
            title = entry.fields.get('title', '')
            if not title:
                return _unresolved(entry, 'pubmed', 'No title or PMID')
            from jikeyan_mcp.local_search.pubmed import search_title_candidates
            ids, records = search_title_candidates(
                http, title, _first_author_surname(entry.fields.get('author', '')),
                entry.fields.get('year', ''), retmax=5,
            )
        if not ids:
            return _unresolved(entry, 'pubmed', 'No PubMed record')
        if pmid:
            data = http.get_json(
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
                params={'db': 'pubmed', 'retmode': 'json', 'id': ','.join(ids)},
            )
            records = data.get('result', {}) if isinstance(data, Mapping) else {}
        for id_ in ids:
            record = records.get(str(id_)) if isinstance(records, Mapping) else None
            if pmid and (record is None or isinstance(record, Mapping) and 'error' in record):
                return ReferenceVerdict(
                    entry.key, 'MISMATCH', pmid, ('pmid',), 'pubmed', 'PMID 在 PubMed 中不存在'
                )
            matches_title = isinstance(record, Mapping) and _title_equivalent(
                _normalized(entry.fields.get('title')), _normalized(record.get('title'))
            )
            if isinstance(record, Mapping) and (pmid or matches_title):
                return _track_result(entry, record, str(id_), 'pubmed')
        return _unresolved(entry, 'pubmed', 'No matching PubMed record')
    except Exception as error:
        return _lookup_failure(entry, 'pubmed', error)


def merge_status(crossref: str, pubmed: str) -> str:
    """A mismatch wins; a verified track wins over unresolved; unknowns stay unresolved."""
    states = {crossref, pubmed}
    if 'mismatch' in states:
        return 'mismatch'
    if not states <= {'verified', 'unresolved'}:
        return 'unresolved'
    return 'verified' if 'verified' in states else 'unresolved'


_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

CONTACT_EMAIL_REQUIRED = (
    '文献核验与撞题检索工具需要你自己的联系邮箱：请设置环境变量 JIKEYAN_CONTACT_EMAIL。'
    'Crossref 与 NCBI 要求公开接口的调用方留下联系方式；该邮箱只随请求发给它们，'
    '不会发送给极科研服务端，也不会落盘。'
)


def require_contact_email(value: str) -> str:
    """Return the stripped email, or raise ValueError with a fixed message.

    Only the shape is checked; whether the mailbox exists is not verified.
    """
    email = (value or '').strip()
    if not _EMAIL_PATTERN.match(email):
        raise ValueError(CONTACT_EMAIL_REQUIRED)
    return email


def verify_references(
    bibtex: str, *, contact_email: str = '', ncbi_api_key: str = '',
    http: HttpClient | None = None,
) -> dict:
    if http is None:
        # Real network access always goes out under the caller's own address.
        contact_email = require_contact_email(contact_email)
    if len(bibtex.encode('utf-8')) > 200 * 1024:
        raise ValueError('BibTeX exceeds 200 KB')
    entries = parse_bibtex(bibtex)
    if len(entries) > 50:
        raise ValueError('BibTeX exceeds 50 entries')
    client = http if http is not None else UrlLibHttpClient(
        contact_email=contact_email, ncbi_api_key=ncbi_api_key
    )
    notes = ['数据来源：Crossref / NCBI PubMed；不代表其背书。']
    if find_duplicate_keys(entries):
        notes.append('存在重复的 BibTeX key。')
    if find_duplicate_dois(entries):
        notes.append('存在重复的 DOI。')
    output = []
    failed_entries = 0
    mapping = {'REAL': 'verified', 'MISMATCH': 'mismatch', 'UNRESOLVED': 'unresolved'}
    for entry in entries:
        verdicts = [verify_crossref_track(entry, client), verify_pubmed_track(entry, client)]
        tracks = []
        for source, verdict in zip(('crossref', 'pubmed'), verdicts):
            track = {
                'source': source, 'status': mapping[verdict.status],
                'identifier': verdict.identifier,
                'differing_fields': list(verdict.differing_fields),
                'message': verdict.message,
            }
            if verdict.lookup_failed:
                track['lookup_failed'] = True
            tracks.append(track)
        failed = any(v.lookup_failed for v in verdicts)
        failed_entries += int(failed)
        status = merge_status(*(t['status'] for t in tracks))
        missing_identifier = any(
            v.message in ('DOI 在 Crossref 中不存在', 'PMID 在 PubMed 中不存在') for v in verdicts
        )
        if missing_identifier:
            advice = '标识符在数据库中不存在，请核对 DOI/PMID。'
        elif failed and status == 'verified':
            advice = '部分数据库查询失败，请稍后重试。另一数据库查询失败。'
        elif failed and status == 'unresolved':
            advice = '部分数据库查询失败，请稍后重试。'
        elif status == 'verified' and any(t['status'] == 'unresolved' for t in tracks):
            advice = '一条数据库记录一致，另一条未解析；可进一步核对。'
        else:
            advice = {
                'verified': '已解析的题录元数据一致。',
                'mismatch': '请核对标出的题录字段。',
                'unresolved': '未能解析，请人工核对题录。',
            }[status]
        output.append({
            'key': entry.key, 'status': status,
            'differing_fields': sorted({field for t in tracks for field in t['differing_fields']}),
            'tracks': tracks, 'advice': advice,
        })
    if failed_entries:
        notes.append(f'有 {failed_entries} 条的查询因网络或限流失败，结果不完整，建议稍后重试。')
    return {
        'summary': {
            'total': len(output),
            **{
                s: sum(e['status'] == s for e in output)
                for s in ('verified', 'mismatch', 'unresolved')
            },
        },
        'entries': output,
        'disclaimer': (
            '结论仅表示题录元数据与公开数据库的一致性，不构成对文献真伪或质量的判断；'
            'unresolved 常见于会议摘要、标准、信件等无 DOI 的条目。'
        ),
        'notes': notes,
        'limits': {'max_entries': 50},
    }
