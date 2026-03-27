"""Generate summaries / exports into `reports/`."""

from pathlib import Path


def export_markdown_stub(output_dir: Path, *, title: str = "ideavault-review") -> Path:
    """
    Placeholder writer for future report generation.

    TODO: query items, template engine, charts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{title}.md"
    path.write_text("# IdeaVault Flow\n\n_TODO: generated content_\n", encoding="utf-8")
    return path
