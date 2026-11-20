"""User-approved, item-specific search aliases; no material or gold expansion."""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


@lru_cache(maxsize=1)
def load_aliases():
    path = Path(__file__).resolve().parents[2] / 'data/reference_data/approved_search_aliases.json'
    return json.loads(path.read_text(encoding='utf-8'))


def query_variants(query):
    normalized = normalize(query)
    if any(term in normalized for term in ('保養', '維修', '工程', '換鎖', '檢測', '安裝', '零件更換', '廢棄', '回收')):
        return [query]
    # The existing query enricher appends reference terms after the original name.
    matches = [r for r in load_aliases() if normalized == normalize(r['original'])
               or normalized.startswith(normalize(r['original']) + ' ')]
    if not matches:
        return [query]
    row = max(matches, key=lambda r: len(normalize(r['original'])))
    variants, seen = [], set()
    for text in [query, row['original'], row['canonical']] + row['aliases']:
        key = normalize(text)
        if key not in seen:
            variants.append(text)
            seen.add(key)
    return variants


def search_variants(retriever, query, top_k, threshold):
    variants = query_variants(query)
    if len(variants) == 1:
        return retriever.search(query=query, top_k=top_k, threshold=threshold)
    found = {}
    for variant in variants:
        for candidate in retriever.search(query=variant, top_k=top_k, threshold=threshold):
            item = dict(candidate)
            key = item['index']
            if key not in found or float(item['similarity']) > float(found[key]['similarity']):
                item['matched_search_query'] = variant
                item['original_search_query'] = query
                item['search_alias_applied'] = variant != query
                found[key] = item
    return sorted(found.values(), key=lambda r: float(r['similarity']), reverse=True)[:top_k]
