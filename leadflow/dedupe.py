"""Find the same person across sources and merge them into one lead.

Match rules, strongest first:
  1. same email
  2. same phone (E.164)
  3. same business domain AND very similar name ("Mohammed Ali" / "Mohamed Ali")
"""
from difflib import SequenceMatcher

from .normalize import Lead

NAME_SIMILARITY = 0.88
FILLABLE = ("email", "phone", "company", "job_title", "country", "budget", "timeline", "domain")


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_same(a: Lead, b: Lead) -> str | None:
    if a.email and a.email == b.email:
        return "email"
    if a.phone and a.phone == b.phone:
        return "phone"
    if a.domain and a.domain == b.domain and similar(a.name, b.name) >= NAME_SIMILARITY:
        return "name+domain"
    return None


def merge(keep: Lead, dup: Lead) -> Lead:
    """Fill gaps in `keep` from `dup`; keep both messages."""
    for f in FILLABLE:
        if getattr(keep, f) in (None, "") and getattr(dup, f) not in (None, ""):
            setattr(keep, f, getattr(dup, f))
    if dup.business_email and not keep.business_email:
        keep.business_email = True
    if dup.message and dup.message != keep.message:
        keep.message = f"{keep.message}\n---\n{dup.message}" if keep.message else dup.message
    keep.merged_from.append(dup.ref)
    return keep


def dedupe(leads: list[Lead]) -> tuple[list[Lead], list[tuple[str, str, str]]]:
    """Returns (unique leads, [(kept_ref, dropped_ref, rule), ...])."""
    unique: list[Lead] = []
    log = []
    for lead in leads:
        for existing in unique:
            rule = is_same(existing, lead)
            if rule:
                merge(existing, lead)
                log.append((existing.ref, lead.ref, rule))
                break
        else:
            unique.append(lead)
    return unique, log
