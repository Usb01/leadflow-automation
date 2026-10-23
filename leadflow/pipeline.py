from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .dedupe import dedupe
from .enrich import enrich
from .scoring import load_config, score
from .sources import load_mappings, read_source


@dataclass
class RunResult:
    leads: list = field(default_factory=list)
    rejected: list = field(default_factory=list)     # (ref, reason, raw)
    merges: list = field(default_factory=list)       # (kept, dropped, rule)
    per_source: Counter = field(default_factory=Counter)

    @property
    def grades(self) -> Counter:
        return Counter(l.grade for l in self.leads)


def run(files: dict[str, Path], scoring_cfg: Path | None = None, default_country: str = "SA") -> RunResult:
    """files maps a source name (key in config/sources.json) to its CSV export."""
    mappings = load_mappings()
    cfg = load_config(scoring_cfg)
    res = RunResult()
    staged = []

    for source, path in files.items():
        if source not in mappings:
            raise ValueError(f"no column mapping for source '{source}' in config/sources.json")
        for lead, error, raw in read_source(path, source, mappings[source], default_country):
            res.per_source[source] += 1
            if error:
                res.rejected.append((raw["_ref"], error, raw))
            else:
                staged.append(enrich(lead))

    unique, res.merges = dedupe(staged)
    res.leads = sorted((score(l, cfg) for l in unique), key=lambda l: -l.score)
    return res
