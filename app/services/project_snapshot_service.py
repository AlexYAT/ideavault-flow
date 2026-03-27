"""Deterministic «/review» snapshot; optional LLM restyling over same facts."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.tables import Item
from app.repositories import items_repo
from app.services.llm_enhancement import try_enhance_review
from app.utils.source_dedupe import normalize_note_text


def _unique_recent_lines(
    rows: Sequence[Item],
    *,
    max_lines: int = 5,
    max_chars: int = 72,
) -> list[str]:
    """Recent note snippets; collapse exact-normalized duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        key = normalize_note_text(row.text)
        if key in seen:
            continue
        seen.add(key)
        line = row.text.strip().replace("\n", " ")
        if len(line) > max_chars:
            line = line[: max_chars - 1] + "…"
        out.append(line)
        if len(out) >= max_lines:
            break
    return out


def _gaps_hints(corpus_lower: str, n_notes: int) -> list[str]:
    """Short gap bullets from simple keyword presence rules."""
    hints: list[str] = []
    if n_notes == 0:
        return hints
    if n_notes < 3:
        hints.append("Мало заметок — разбейте мысли на несколько коротких записей.")
    if "mvp" not in corpus_lower and "minimum" not in corpus_lower:
        hints.append("Нет явного фокуса на MVP — добавьте, если это якорь продукта.")
    if "пользовател" not in corpus_lower and "юзер" not in corpus_lower and "customer" not in corpus_lower:
        hints.append("Нет пользовательских сценариев или ЦА — зафиксируйте, для кого продукт.")
    if "монет" not in corpus_lower and "деньг" not in corpus_lower and "pricing" not in corpus_lower:
        hints.append("Не упоминаются деньги/монетизация — стоит хотя бы гипотезу.")
    return hints[:3]


def _baseline_empty(focus: str) -> str:
    return "\n".join(
        [
            focus,
            "Записей в области: 0",
            "",
            "Добавьте заметки: + текст",
            "",
            "Пробелы:",
            "• Нет данных — начните с одной короткой заметки.",
        ]
    )


def _baseline_populated(
    focus: str,
    n: int,
    snippets: list[str],
    gaps: list[str],
) -> str:
    lines = [
        focus,
        f"Всего записей в области: {n}",
        "",
        "Заметки (свежие, без повторов):",
    ]
    if not snippets:
        lines.append("— пусто. Добавьте: + текст")
    else:
        for s in snippets:
            lines.append(f"• {s}")
    lines.append("")
    lines.append("Пробелы (эвристика):")
    if not gaps:
        lines.append("— явных пробелов по ключевым словам не найдено.")
    else:
        for g in gaps:
            lines.append(f"• {g}")
    return "\n".join(lines)


def format_project_review(db: Session, *, current_project: str | None) -> str:
    """
    Build compact snapshot; optionally LLM-полированный тот же контент при ``LLM_ENABLED``.

    Scope: ``current_project`` → только этот ``project``; ``None`` → все заметки.
    """
    limit = 40
    if current_project is not None:
        rows = list(items_repo.list_items(db, project=current_project, limit=limit))
        focus = f"Фокус: проект «{current_project}»"
    else:
        rows = list(items_repo.list_items(db, project=None, limit=limit))
        focus = "Фокус: все заметки (проект не задан)"

    n = len(rows)
    if n == 0:
        return _baseline_empty(focus)

    snippets = _unique_recent_lines(rows, max_lines=5)
    corpus = " ".join(r.text.lower() for r in rows)
    gaps = _gaps_hints(corpus, n)
    baseline = _baseline_populated(focus, n, snippets, gaps)

    enhanced = try_enhance_review(
        get_settings(),
        current_project=current_project,
        focus_line=focus,
        n_notes=n,
        snippets=snippets,
        gap_bullets=gaps,
        source_note_ids=tuple(r.id for r in rows[:40]),
    )
    return enhanced if enhanced else baseline
