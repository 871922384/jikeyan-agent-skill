"""Shared bounded PubMed title candidate retrieval."""
import re
from collections.abc import Mapping

BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'


def search_title_candidates(http, title, author='', year='', retmax=10):
    suffix = (f' AND {author}[Author]' if author else '') + (f' AND {year}[Date - Publication]' if year else '')
    words = re.findall(r'[^\W_]+', title, flags=re.UNICODE)
    queries = [f'"{title}"[Title]{suffix}', ' AND '.join(f'{word}[Title]' for word in words) + suffix]
    ids = []
    for query in queries:
        if not query.strip():
            break
        data = http.get_json(BASE + 'esearch.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'term': query, 'retmax': str(retmax)})
        if not isinstance(data, Mapping) or not isinstance(data.get('esearchresult'), Mapping) or not isinstance(data['esearchresult'].get('idlist'), list):
            raise ValueError('invalid PubMed response')
        ids = data['esearchresult']['idlist'][:retmax]
        if ids:
            break
    if not ids:
        return [], {}
    data = http.get_json(BASE + 'esummary.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'id': ','.join(ids)})
    if not isinstance(data, Mapping) or not isinstance(data.get('result'), Mapping):
        raise ValueError('invalid PubMed response')
    return ids, data['result']
