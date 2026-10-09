"""Reading drive facts from how retailers write them: part numbers, capacities, conditions."""

import re
from collections.abc import Iterable, Sequence
from decimal import Decimal

# Normalized values keyed by name; intended_use is a list, the rest single values.
Specifications = dict[str, str | list[str]]

# Condition rules, in order: the first whose pattern matches (case-insensitively) names the
# condition. disktracker keeps them, editable on its Admin page.
ConditionRules = Sequence[tuple[re.Pattern[str], str]]
# "4TB", "1.92TB", "500 GB" — but not a link speed like "6Gb/s".
CAPACITY = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s?(TB|GB)\b(?!/s)")


# Manufacturer part numbers as printed in titles, one alternative per maker's format.
MAKER_MPN = re.compile(
    r"(?<![0-9A-Z/-])("
    # Seagate: ST18000NM003D, ST1000NM0023, and older ST32000444SS / ST3500312CS.
    r"ST\d{3,8}[A-Z]{2}(?:[0-9A-Z]{3,4})?"
    # WD / HGST enterprise: WUH721816AL5205, HUS726T4TAL4205; Hitachi SSD: HUSSL4010BSS600.
    r"|(?:WUH|WUS|HUS|HUH|HUA)\d{3}[0-9A-Z]{3}[A-Z]{2,3}[0-9A-Z]{3,4}"
    r"|HUS[A-Z]{2}\d{4}[A-Z]{3}\d{3}"
    # WD: WD2000FYYZ, WD80EAAZ, WD6001F4PZ; WD SSD: WDS100T4B0E.
    r"|WDS?\d{2,4}[A-Z][0-9A-Z]{2,4}"
    # Toshiba: MG07ACA14TEY, MQ01ABD100(V), MK1001TRKB; Toshiba SSD: THNSNK256GVN8.
    r"|MG\d{2}[A-Z]{3}\d{2,3}[A-Z]{1,3}"
    r"|MQ\d{2}[A-Z]{3}\d{3}[A-Z]?"
    r"|MK\d{4}[A-Z]{3,4}"
    r"|THN[A-Z]{3}\d{3}G[A-Z]{2,3}\d"
    # Intel SSD: SSDSCKKB240GZR; Micron SSD: MTFDDAV240TDU.
    r"|SSDSC[0-9A-Z]{6,12}"
    r"|MTFD[A-Z]{3}\d{3,4}[A-Z]{3}"
    # Kingston SSD: SA400M8/240G, SUV500M8/240G; SanDisk SSD: SDSSDE61-1T00-G25.
    r"|S(?:A400|UV500)[0-9A-Z]{0,3}/\d{3,4}G"
    r"|SDSSD[0-9A-Z]{2,4}-\d[0-9A-Z]{3}(?:-[0-9A-Z]{3})?"
    r")(?![0-9A-Z/-])"
)


def mpn_from_title(title: str) -> str | None:
    match = MAKER_MPN.search(title.upper())
    return match[1] if match else None


def capacity_in(text: str) -> int | None:
    """The first capacity written in the text, in whole decimal gigabytes."""
    match = CAPACITY.search(text)
    if not match:
        return None
    return int(Decimal(match[1]) * (1000 if match[2] == "TB" else 1))


def condition_rules(rules: Iterable[tuple[str, str]]) -> ConditionRules:
    """(pattern, condition) pairs, in order, ready to read with."""
    return [(re.compile(pattern, re.IGNORECASE), condition) for pattern, condition in rules]


def condition_in(rules: ConditionRules, *texts: str | None) -> str | None:
    """The condition of the first rule matching any of the texts: rule order decides, so a
    title saying "Renewed" can outrank a condition field saying "New"."""
    for pattern, condition in rules:
        if any(text and pattern.search(text) for text in texts):
            return condition
    return None


def media_type_named(text: str) -> str | None:
    """Reads "Hard Drive", "HDDs", "SSD", "Solid State Drives", "microSD card" and the like."""
    lowered = text.lower()
    if re.search(r"micro ?sd|\bsd(hc|xc)?\b card", lowered):
        return "flash_card"
    if re.search(r"\bssds?\b|solid state", lowered):
        return "ssd"
    if re.search(r"hard drive|\bhdds?\b", lowered):
        return "hdd"
    return None


def form_factor_named(text: str) -> str | None:
    """Reads "3.5", "3.5in", '3.5"', "3.5''", "3.5 Inch", "3.5-Inch", "M.2", "microSD" and the
    like."""
    lowered = text.lower()
    if re.search(r"micro ?sd", lowered):
        return "microsd"
    for size, value in (("3", "3_5"), ("2", "2_5")):
        if re.search(rf'{size}\.5(?:[\s-]?(?:inch|in\b)|"|\'\'|$)', lowered):
            return value
    return "m_2" if "m.2" in lowered else None


def interface_named(text: str) -> str | None:
    """Reads "SATA III", "SAS-4", "PCIe Gen 4.0 x4", "NVMe", "USB 3.0" and the like."""
    lowered = text.lower()
    for value, pattern in (
        ("nvme_pcie", r"\bnvme\b|\bpcie\b"),
        ("sas", r"\bsas\b"),
        ("sata", r"\bsata\b"),
        ("usb", r"\busb\b"),
    ):
        if re.search(pattern, lowered):
            return value
    return None


# Only where the text states it: one product line can ship both, model by model.
RECORDING = (
    ("cmr", r"\bcmr\b|conventional magnetic recording"),
    ("smr", r"\bsmr\b|shingled magnetic recording"),
)
# What the maker markets a drive for, by product line or as the text states it. A bare
# "Desktop" is left out: it names an external enclosure style as often as a drive's use.
INTENDED_USES = (
    ("nas", r"\bnas\b|ironwolf|\b(wd|western digital) red\b|toshiba n300"),
    ("surveillance", r"surveillance|skyhawk|\b(wd|western digital) purple\b|toshiba s300"),
    (
        "enterprise",
        (
            r"enterprise|data ?cent(er|re)|\bexos\b|ultrastar|constellation"
            r"|\b(wd|western digital) gold\b"
        ),
    ),
    ("desktop", r"barracuda|\b(wd|western digital) blue\b|toshiba p300"),
    ("archive", r"\barchive\b"),
)


def recording_named(text: str) -> str | None:
    """Reads "CMR", "SMR" and their spelled-out names."""
    lowered = text.lower()
    return next((value for value, pattern in RECORDING if re.search(pattern, lowered)), None)


def intended_use_named(text: str) -> list[str]:
    """Reads "NAS", "Surveillance", "Enterprise" and product lines such as IronWolf or WD Purple."""
    lowered = text.lower()
    return [value for value, pattern in INTENDED_USES if re.search(pattern, lowered)]


def specifications(
    media_type: str | None,
    form_factor: str | None,
    interface: str | None,
    recording_type: str | None = None,
    intended_use: list[str] | None = None,
) -> Specifications | None:
    """The specifications that were found, or None when nothing was."""
    found: dict[str, str | list[str] | None] = {
        "media_type": media_type,
        "form_factor": form_factor,
        "interface": interface,
        "recording_type": recording_type,
        "intended_use": intended_use or None,
    }
    known = {key: value for key, value in found.items() if value is not None}
    return known or None


def specifications_in_title(title: str) -> Specifications | None:
    """Whatever the title says of the drive's specifications."""
    return specifications(
        media_type_named(title),
        form_factor_named(title),
        interface_named(title),
        recording_named(title),
        intended_use_named(title),
    )


# Makers as sources write them, and the store brands that sell under their own name. HGST
# was bought by Western Digital and is folded into it; OEM labels (Dell, HP) are not makers.
MAKERS = (
    ("Western Digital", r"western digital|\bwd(?:_|\b)|\bhgst\b|ultrastar"),
    ("Seagate", r"\bseagate\b"),
    ("Toshiba", r"\btoshiba\b"),
    ("Intel", r"\bintel\b"),
    ("Samsung", r"\bsamsung\b"),
    ("Micron", r"\bmicron\b"),
    ("Crucial", r"\bcrucial\b"),
    ("Kingston", r"\bkingston\b"),
    ("SanDisk", r"\bsandisk\b"),
    ("Avolusion", r"\bavolusion\b"),
    ("MaxDigital", r"\bmaxdigital(?:data)?\b|\bmdd\b"),
)


# Store brands: sold by one store only, so their drives have no MPN any other store shares.
STORE_BRANDS = frozenset({"Avolusion", "MaxDigital"})


def maker_named(text: str) -> str | None:
    """Reads who made a drive, by maker or store brand; None when the text names neither."""
    lowered = text.lower()
    return next((maker for maker, pattern in MAKERS if re.search(pattern, lowered)), None)
