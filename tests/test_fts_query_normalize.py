"""Нормализация free-text перед FTS MATCH (RAG и прочие вызовы build_fts_match)."""

from app.utils.fts_query import build_fts_match, normalize_fts_query_text


def test_normalize_hyphen_and_case() -> None:
    assert normalize_fts_query_text("  IdeaVault-FLOW  ") == "ideavault flow"
    assert normalize_fts_query_text("ideavault-flow") == "ideavault flow"


def test_build_fts_match_splits_hyphenated_query() -> None:
    expr = build_fts_match("ideavault-flow")
    assert expr is not None
    assert " AND " in expr
    assert "ideavault" in expr.lower()
    assert "flow" in expr.lower()
