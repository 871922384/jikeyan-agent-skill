"""Shallow, independently testable public-source topic searches."""
from datetime import datetime, timezone
import re
from collections.abc import Mapping

from jikeyan_mcp.local_search.pubmed import BASE
from jikeyan_mcp.local_search.references import UrlLibHttpClient, require_contact_email, lookup_error_category

STOP = frozenset('a an the of in on for to and or with by from vs trial review systematic'.split())
GENERIC = frozenset('therapy treatment patient patients study studies effect effects clinical analysis outcome outcomes use using versus comparison evaluation assessment role impact based approach among between new novel continuous'.split())
TYPES = frozenset(('intervention_trial', 'observational', 'systematic_review', 'diagnostic_or_prognostic', 'other'))
SENSITIVITIES = ('narrow', 'medium', 'broad')
PROSPERO = 'PROSPERO 未检索（其使用条款对自动化访问有限制，本工具不访问）；是否检索、如何检索由你自行决定，入口 https://www.crd.york.ac.uk/prospero/ 。'
GROUP_ERROR = '概念分组须为 1 至 6 组，每组 1 至 8 个有效字符串，每个最多 60 个字符。'


def _terms(text, *, filtered=True):
    words = (w.casefold() for w in re.findall(r'[^\W_]+', text, re.UNICODE))
    return list(dict.fromkeys(w for w in words if not filtered or w not in STOP | GENERIC))


def _validate_groups(groups):
    if (not isinstance(groups, list) or not 1 <= len(groups) <= 6 or
        any(not isinstance(group, list) or not 1 <= len(group) <= 8 or
            any(not isinstance(term, str) or not term.strip() or len(term) > 60 or
                any(not c.isprintable() for c in term) or
                not any(c.isalnum() for c in term) for term in group)
            for group in groups)):
        raise ValueError(GROUP_ERROR)
    return [[term.strip() for term in group] for group in groups]


def _heuristic_terms(title, keywords):
    text = ' '.join([title, *keywords])
    words = _terms(text)
    if len(words) < 2:
        words = _terms(text, filtered=False)
    if not words:
        raise ValueError('题名须包含可检索词项。')
    return sorted(words, key=len, reverse=True)


def _quote(term):
    if re.fullmatch(r'[^\W_]+', term, re.UNICODE):
        return term
    return '"' + term.replace('\\', '\\\\').replace('"', '\\"') + '"'


def render_variants(title, keywords, concept_groups=None):
    if concept_groups is not None:
        groups = _validate_groups(concept_groups)
        clauses = ['(' + ' OR '.join(map(_quote, group)) + ')' for group in groups]
        return {'narrow': ' AND '.join(_quote(group[0]) for group in groups),
                'medium': ' AND '.join(clauses), 'broad': ' AND '.join(clauses[:2])}
    terms = _heuristic_terms(title, keywords)
    n = len(terms)
    medium_count = min(n, max(2, (2 * n + 2) // 3))
    return {'narrow': ' AND '.join(map(_quote, terms)),
            'medium': ' AND '.join(map(_quote, terms[:medium_count])),
            'broad': ' AND '.join(map(_quote, terms[:2]))}


def _basis(title, terms):
    found = []
    seen = set()
    for term in terms:
        key = term.casefold()
        if key not in seen and key in title.casefold():
            found.append(term)
            seen.add(key)
    if not found:
        return '题名未包含检索词（命中可能来自摘要或关键词）'
    return f"题名包含检索词：{'、'.join(found)}（共 {len(found)} 个）"


def _clinical(http, query, terms):
    data = http.get_json('https://clinicaltrials.gov/api/v2/studies', params={
        'query.term': query, 'pageSize': '10', 'countTotal': 'true',
        'fields': 'NCTId,BriefTitle,OverallStatus,StartDate,CompletionDate,Condition,InterventionName',
    })
    if not isinstance(data, Mapping) or not isinstance(data.get('studies'), list):
        raise ValueError('invalid response')
    total = int(data['totalCount'])
    hits = []
    for study in data['studies'][:10]:
        section = study['protocolSection']; ident = section['identificationModule']; status = section.get('statusModule', {})
        id_ = ident['nctId']; title = ident.get('briefTitle', '')
        hits.append({'id': id_, 'title': title, 'url': f'https://clinicaltrials.gov/study/{id_}', 'status_or_year': status.get('overallStatus', ''), 'match_basis': _basis(title, terms),
                     'start_date': status.get('startDateStruct', {}).get('date', ''), 'completion_date': status.get('completionDateStruct', {}).get('date', ''),
                     'conditions': section.get('conditionsModule', {}).get('conditions', []), 'interventions': [i.get('name', '') for i in section.get('armsInterventionsModule', {}).get('interventions', [])]})
    return total, hits


def _pubmed(http, query, terms):
    query = f'({query}) AND systematic[sb]'
    data = http.get_json(BASE + 'esearch.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'term': query, 'retmax': '10'})
    result = data['esearchresult']; total = int(result['count']); ids = result['idlist'][:10]
    if not ids:
        return query, total, []
    data = http.get_json(BASE + 'esummary.fcgi', params={'db': 'pubmed', 'retmode': 'json', 'id': ','.join(ids)})
    records = data['result']; hits = []
    for id_ in ids:
        record = records[str(id_)]; title = record.get('title', '')
        year = re.search(r'\b(?:19|20)\d{2}\b', record.get('pubdate', ''))
        hits.append({'id': str(id_), 'title': title, 'url': f'https://pubmed.ncbi.nlm.nih.gov/{id_}/', 'status_or_year': year.group() if year else '', 'journal': record.get('fulljournalname', record.get('source', '')), 'match_basis': _basis(title, terms)})
    return query, total, hits


def check_topic_collision(title, keywords=None, study_type='other', *, concept_groups=None, contact_email='', ncbi_api_key='', http=None):
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise ValueError('题名须为 1 至 300 个字符。')
    if keywords is None:
        keywords = []
    if not isinstance(keywords, list) or len(keywords) > 10 or any(not isinstance(k, str) or not k.strip() or len(k) > 60 for k in keywords):
        raise ValueError('关键词须为最多 10 个非空字符串，每个最多 60 个字符。')
    if not isinstance(study_type, str) or study_type not in TYPES:
        raise ValueError('研究类型无效。')
    groups = _validate_groups(concept_groups) if concept_groups is not None else None
    email = require_contact_email(contact_email) if http is None else contact_email
    queries = render_variants(title, keywords, groups)
    if groups is not None:
        variant_terms = {'narrow': [group[0] for group in groups],
                         'medium': [term for group in groups for term in group],
                         'broad': [term for group in groups[:2] for term in group]}
    else:
        terms = _heuristic_terms(title, keywords)
        n = len(terms)
        variant_terms = {'narrow': terms, 'medium': terms[:min(n, max(2, (2 * n + 2) // 3))], 'broad': terms[:2]}
    client = http if http is not None else UrlLibHttpClient(contact_email=email, ncbi_api_key=ncbi_api_key)
    if isinstance(client, UrlLibHttpClient):
        client.max_requests = 9
        client.request_count = 0
    date = datetime.now(timezone.utc).date().isoformat()
    sources = []; notes = ['命中总数由来源返回；实际取回条数最多为 10，零命中不代表不存在相关研究。']
    for source in ('clinicaltrials_gov', 'pubmed_reviews'):
        variants = []
        for sensitivity in SENSITIVITIES:
            query = queries[sensitivity]
            terms = variant_terms[sensitivity]
            actual_query = f'({query}) AND systematic[sb]' if source == 'pubmed_reviews' else query
            try:
                if source == 'clinicaltrials_gov':
                    total, hits = _clinical(client, query, terms)
                else:
                    actual_query, total, hits = _pubmed(client, query, terms)
                if total < 0:
                    raise ValueError('invalid count')
                failed = False
                category = None
            except Exception as error:
                total, hits, failed = None, [], True
                category = lookup_error_category(error)
            variant = {'sensitivity': sensitivity, 'query': actual_query, 'total_count': total, 'returned': len(hits), 'hits': hits, 'lookup_failed': failed}
            if failed:
                variant['failure_category'] = category
            variants.append(variant)
        counts = [v['total_count'] for v in variants]
        if any(count is not None and count > 2000 for count in counts):
            warning = '某检索式命中过多，仅供参考；请提供 concept_groups（同义词分组）以收窄。'
            if warning not in notes:
                notes.append(warning)
            if groups is None and '当前检索式由启发式生成，质量有限。' not in notes:
                notes.append('当前检索式由启发式生成，质量有限。')
        inversion = any(a > b for a, b in zip(counts, counts[1:]) if a is not None and b is not None)
        monotone = all(count is not None for count in counts) and not inversion
        if any(v['lookup_failed'] for v in variants) and '有检索失败，结果不完整' not in notes:
            notes.append('有检索失败，结果不完整')
        if inversion and '检索式或来源行为异常，结果不可靠' not in notes:
            notes.append('检索式或来源行为异常，结果不可靠')
        provider = 'ClinicalTrials.gov（美国国家医学图书馆）' if source == 'clinicaltrials_gov' else 'NCBI PubMed（美国国家医学图书馆）'
        sources.append({'source': source, 'variants': variants, 'monotone_ok': monotone, 'attribution': f'数据来自 {provider}，经本工具截取与摘要，检索于 {date}。'})
    return {'candidate': {'title': title, 'keywords': keywords, 'study_type': study_type, 'concept_groups': groups if groups is not None else '启发式'}, 'sources': sources, 'not_searched': [{'source': 'prospero', 'reason': PROSPERO, 'manual_url': 'https://www.crd.york.ac.uk/prospero/'}], 'retrieved_at': date, 'disclaimer': '零命中不等于没有人做过；本工具只返回公开来源的命中与检索式，不判断选题能否开展。', 'notes': notes}
