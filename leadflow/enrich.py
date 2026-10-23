FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.com", "yandex.com", "msn.com",
}
DISPOSABLE = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "yopmail.com",
              "trashmail.com", "sharklasers.com"}


def email_domain(email: str | None) -> str | None:
    return email.split("@", 1)[1] if email and "@" in email else None


def company_from_domain(domain: str) -> str:
    """acme-logistics.com.sa -> Acme Logistics"""
    base = domain.split(".")[0]
    return " ".join(w.capitalize() for w in base.replace("_", "-").split("-"))


def enrich(lead):
    domain = email_domain(lead.email)
    if domain in DISPOSABLE:
        lead.reasons.append("disposable email domain")
    lead.business_email = bool(domain) and domain not in FREE_MAIL and domain not in DISPOSABLE
    if lead.business_email:
        lead.domain = domain
        if not lead.company:
            lead.company = company_from_domain(domain)
    return lead
