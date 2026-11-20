import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from retrieval.approved_aliases import load_aliases, query_variants, search_variants


def test_approved_names_only():
    assert len(load_aliases()) == 158
    assert '保鮮盒' in query_variants('綺麗密封盒L')
    assert '保鮮盒' in query_variants('綺麗密封盒M 塑膠製品')
    assert query_variants('綺麗密封盒XL') == ['綺麗密封盒XL']
    assert query_variants('精密平斜石刀組') == ['精密平斜石刀組']
    assert query_variants('硬碟維修') == ['硬碟維修']
    assert not any('polypropylene' in t for t in query_variants('綺麗密封盒L'))


def test_merge_preserves_scores_and_deduplicates():
    class Retriever:
        def search(self, query, top_k, threshold):
            return [dict(index=1, similarity=.9 if query == '保鮮盒' else .8)]
    result = search_variants(Retriever(), '綺麗密封盒L', 3, .7)
    assert len(result) == 1
    assert result[0]['similarity'] == .9
    assert result[0]['matched_search_query'] == '保鮮盒'


def test_unknown_query_unchanged():
    class Retriever:
        def search(self, **kwargs):
            assert kwargs == dict(query='未知品項', top_k=3, threshold=.7)
            return []
    assert search_variants(Retriever(), '未知品項', 3, .7) == []
