from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES = Path(__file__).parent / "templates"


def render(result, new, known, sink_summary: dict, out: Path) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape())
    total_in = sum(result.per_source.values())
    html = env.get_template("report.html").render(
        r=result, new=new, known=known, sink=sink_summary, total_in=total_in,
        generated=datetime.now().strftime("%d %b %Y %H:%M"),
        grade_counts={g: result.grades.get(g, 0) for g in "ABC"},
    )
    out.write_text(html, encoding="utf-8")
    return out
