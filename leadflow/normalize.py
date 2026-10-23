"""Clean up raw lead fields coming from forms, ad exports and spreadsheets."""
import re
from dataclasses import dataclass, field

EMAIL = re.compile(r"^[a-z0-9._%+'-]+@[a-z0-9.-]+\.[a-z]{2,}$")

# country -> (dial code, national number length without trunk 0)
DIAL = {
    "SA": ("966", 9), "AE": ("971", 9), "QA": ("974", 8), "KW": ("965", 8), "BH": ("973", 8), "OM": ("968", 8),
    "PK": ("92", 10), "IN": ("91", 10), "EG": ("20", 10), "GB": ("44", 10), "US": ("1", 10), "JO": ("962", 9),
}
BY_CODE = sorted(((code, cc, n) for cc, (code, n) in DIAL.items()), key=lambda x: -len(x[0]))

COUNTRY_NAMES = {
    "saudi arabia": "SA", "ksa": "SA", "saudi": "SA", "uae": "AE", "united arab emirates": "AE", "qatar": "QA",
    "kuwait": "KW", "bahrain": "BH", "oman": "OM", "pakistan": "PK", "india": "IN", "egypt": "EG",
    "jordan": "JO", "uk": "GB", "united kingdom": "GB", "england": "GB", "usa": "US", "united states": "US",
}


class InvalidLead(ValueError):
    pass


@dataclass
class Lead:
    source: str
    row: int
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    job_title: str | None = None
    country: str | None = None
    budget: int | None = None
    timeline: str | None = None
    message: str | None = None
    submitted_at: str | None = None
    # filled in later
    domain: str | None = None
    business_email: bool = False
    score: int = 0
    grade: str = ""
    reasons: list[str] = field(default_factory=list)
    route: str = ""
    merged_from: list[str] = field(default_factory=list)

    @property
    def ref(self) -> str:
        return f"{self.source}:{self.row}"


def clean_name(raw: str | None) -> str:
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        raise InvalidLead("missing name")
    if name.isupper() or name.islower():
        # "AHMED AL-QAHTANI" / "ahmed al-qahtani" -> "Ahmed Al-Qahtani"
        name = "-".join(part.title() for part in name.split("-"))
        name = re.sub(r"\bAl\b", "Al", name)
    return name[:100]


def clean_email(raw: str | None) -> str | None:
    if not raw or not raw.strip():
        return None
    email = raw.strip().lower().replace(" ", "")
    email = email.removeprefix("mailto:")
    if not EMAIL.match(email):
        raise InvalidLead(f"invalid email '{raw.strip()}'")
    return email


def clean_country(raw: str | None) -> str | None:
    if not raw:
        return None
    v = raw.strip()
    if len(v) == 2 and v.upper() in DIAL:
        return v.upper()
    return COUNTRY_NAMES.get(v.lower())


def clean_phone(raw: str | None, default_country: str = "SA") -> tuple[str | None, str | None]:
    """Return (E.164 phone, country). Accepts '+966 55 123 4567', '00966551234567', '0551234567', etc."""
    if not raw or not str(raw).strip():
        return None, None
    digits = re.sub(r"\D", "", str(raw))
    has_plus = str(raw).strip().startswith("+") or digits.startswith("00")
    digits = digits[2:] if digits.startswith("00") else digits

    if has_plus or (len(digits) > 10 and not digits.startswith("0")):
        for code, cc, n in BY_CODE:
            if digits.startswith(code):
                national = digits[len(code):].lstrip("0")
                if len(national) == n:
                    return f"+{code}{national}", cc
        if 8 <= len(digits) <= 15:
            return f"+{digits}", None  # valid international format, country we don't have rules for
        raise InvalidLead(f"unrecognised phone '{raw}'")

    code, n = DIAL[default_country]
    national = digits.lstrip("0")
    if len(national) != n:
        raise InvalidLead(f"phone '{raw}' has wrong length for {default_country}")
    return f"+{code}{national}", default_country


def clean_budget(raw: str | None) -> int | None:
    """'SAR 15,000', '15k', '10000-20000' (takes the lower bound), '' -> None."""
    if raw is None or not str(raw).strip():
        return None
    v = str(raw).lower().replace(",", "").strip()
    if re.match(r"(under|less than|below|<)", v):
        return 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|m)?", v)
    if not m:
        raise InvalidLead(f"budget '{raw}' is not a number")
    amount = float(m.group(1)) * {"k": 1_000, "m": 1_000_000}.get(m.group(2) or "", 1)
    return int(amount)
