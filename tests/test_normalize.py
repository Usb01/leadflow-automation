import pytest

from leadflow.normalize import InvalidLead, clean_budget, clean_country, clean_email, clean_name, clean_phone


@pytest.mark.parametrize("raw,expected", [
    ("+966 55 123 4567", ("+966551234567", "SA")),
    ("00966 54 222 3344", ("+966542223344", "SA")),
    ("0551234567", ("+966551234567", "SA")),
    ("+971 50 765 4321", ("+971507654321", "AE")),
    ("+92 300 1234567", ("+923001234567", "PK")),
    ("+44 7700 900123", ("+447700900123", "GB")),
    ("+97333445566", ("+97333445566", "BH")),
    ("+962791234567", ("+962791234567", "JO")),
    ("+8613800138000", ("+8613800138000", None)),
    ("", (None, None)),
])
def test_phones(raw, expected):
    assert clean_phone(raw) == expected


def test_local_number_uses_given_country():
    assert clean_phone("0300 1234567", "PK") == ("+923001234567", "PK")


@pytest.mark.parametrize("raw", ["123", "0551234"])
def test_bad_phones(raw):
    with pytest.raises(InvalidLead):
        clean_phone(raw)


def test_email():
    assert clean_email(" Sara.Malik@Gmail.com ") == "sara.malik@gmail.com"
    assert clean_email("mailto:a@b.co") == "a@b.co"
    assert clean_email("") is None
    for bad in ["test@test", "grace@", "no-at-sign.com"]:
        with pytest.raises(InvalidLead):
            clean_email(bad)


def test_names():
    assert clean_name("FAISAL AL-HARBI") == "Faisal Al-Harbi"
    assert clean_name("sara  malik") == "Sara Malik"
    assert clean_name("McDonald Smith") == "McDonald Smith"  # mixed case left alone
    with pytest.raises(InvalidLead):
        clean_name("  ")


@pytest.mark.parametrize("raw,expected", [
    ("SAR 60,000", 60000), ("5k", 5000), ("100k", 100000), ("20000-50000", 20000), ("50000+", 50000),
    ("under 5000", 0), ("", None),
])
def test_budget(raw, expected):
    assert clean_budget(raw) == expected


def test_country():
    assert clean_country("KSA") == "SA" and clean_country("uae") == "AE" and clean_country("Narnia") is None
