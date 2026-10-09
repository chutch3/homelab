import pytest

from listing_text.readers import (
    capacity_in,
    condition_in,
    condition_rules,
    intended_use_named,
    maker_named,
    mpn_from_title,
    recording_named,
    specifications_in_title,
)

Specs = dict[str, str | list[str]]

# The rules disktracker is seeded with.
RULES = condition_rules(
    [
        (r"\bmanufacturer recertified\b", "manufacturer_recertified"),
        (r"\bseller refurbished\b", "refurbished"),
        (r"\bopen box\b", "used"),
        (r"\brecertified\b", "refurbished"),
        (r"\brefurbished\b", "refurbished"),
        (r"\brenewed\b", "refurbished"),
        (r"\bused\b", "used"),
        (r"\bnew\b", "new"),
    ]
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Seagate Exos X20 ST18000NM003D 18TB 7.2K RPM SATA", "ST18000NM003D"),
        ("Dell/Western Digital Ultrastar DC HC550 WUH721816AL5205 0F38376 16TB", "WUH721816AL5205"),
        ("HGST/Dell Ultrastar 7K6000 HUS726040AL4215 0F22824 4TB", "HUS726040AL4215"),
        ("WD Ultrastar DC HC550 WUH721818ALE6L4 18TB SATA", "WUH721818ALE6L4"),
        ("HGST Ultrastar He12 HUH721212ALE604 12TB", "HUH721212ALE604"),
        ("Toshiba 14TB MG07 MG07ACA14TEY 7.2K RPM SATA", "MG07ACA14TEY"),
        ("Toshiba MG08 MG08ACA16TE 16TB", "MG08ACA16TE"),
        ("Dell/Western Digital Ultrastar DC HC320 HUS728T8TAL5200 0B36416 8TB", "HUS728T8TAL5200"),
        ("Western Digital RE WD2000FYYZ 2TB SATA3 Hard Drive", "WD2000FYYZ"),
        ("WD Blue WD80EAAZ 8TB 5640RPM SATA HDD", "WD80EAAZ"),
        ("Western Digital Purple Surveillance WD20EJRX 2TB", "WD20EJRX"),
        ("Western Digital Ae WD6001F4PZ 6TB Datacenter HDD", "WD6001F4PZ"),
        ("WD WD20JDRW 2TB 8MB 5400RPM 2.5 USB 3.0 HDD", "WD20JDRW"),
        ("WD Blue 1TB WDS100T4B0E Gen4 x4 PCIe NVMe 2280 SSD", "WDS100T4B0E"),
        ("Seagate ES ST32000444SS 2TB 7200RPM SAS HDD", "ST32000444SS"),
        ("Seagate ST3500312CS 500GB 8MB 3.5 SATA Hard Drive", "ST3500312CS"),
        ("Seagate ST32000542AS 2TB Baracuda 5900RPM 32MB", "ST32000542AS"),
        ("DELL / Seagate Constellation ES.3 ST1000NM0023 1TB 7200 RPM", "ST1000NM0023"),
        ("TOSHIBA MQ01ABD100 1TB 2.5 Hard Drive", "MQ01ABD100"),
        ("TOSHIBA MQ01ABD100V 1TB 2.5 Hard Drive", "MQ01ABD100V"),
        ("TOSHIBA MK1001TRKB 1TB 7200 RPM 16MB Cache SAS 6Gb", "MK1001TRKB"),
        ("Toshiba THNSNK256GVN8 256GB M.2 2280 6 Gb/s SSD", "THNSNK256GVN8"),
        ("Hitachi Ultrastar HE6 HUSSL4010BSS600 100GB HDD", "HUSSL4010BSS600"),
        ("DELL Intel D3-S4520 240GB SSDSCKKB240GZR M.2 SSD", "SSDSCKKB240GZR"),
        ("DELL MICRON MTFDDAV240TDU 240GB 6Gb/s M.2 2280", "MTFDDAV240TDU"),
        ("Kingston A400 240G SA400M8/240G M.2 2280 SSD", "SA400M8/240G"),
        ("Kingston UV500 SUV500M8/240G 240GB M.2 SSD", "SUV500M8/240G"),
        ("SanDisk 1TB Extreme Portable SSD SDSSDE61-1T00-G25", "SDSSDE61-1T00-G25"),
        ("Dell G14 0HNHWC 16TB 7.2K RPM SAS", None),
        ("Intel D3-S4510 960GB SATA 2.5in SSD", None),
        ("HGST Ultrastar 0F23001 6TB 7200RPM Hard Drive", None),
        ("Kingston 240GB SATA III 2.5 SSD", None),
        ("WD 20TB 3.5 SATA 6Gbps Enterprise Hard Drive", None),
        ("Seagate Expansion 6TB External Hard Drive USB 3.0", None),
    ],
)
def test_mpn_from_title(title: str, expected: str | None) -> None:
    assert mpn_from_title(title) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Avolusion PRO-5X (Grey) 12TB USB 3.0 External Hard Drive", 12000),
        ("Seagate ST1000NM0023 1TB 7200 RPM 128MB Cache SAS", 1000),
        ("MaxDigital 4TB 7200RPM 64MB Cache SATA III", 4000),
        ("Samsung PM893 1.92TB 2.5in SSD", 1920),
        ("Avolusion HD250U3 160GB Ultra Slim Portable", 160),
        ("960GB", 960),
        ("18 TB", 18000),
        ("USB 3.0 Enclosure with 128MB buffer", None),
    ],
)
def test_capacity_in_text_is_whole_gigabytes(text: str, expected: int | None) -> None:
    assert capacity_in(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hard Drive (Refurbished)- w/3 Year Warranty", "refurbished"),
        ("Exos X20 Manufacturer Recertified", "manufacturer_recertified"),
        ("Seller Refurbished", "refurbished"),
        ("Recertified Exos", "refurbished"),
        ("Renewed drive", "refurbished"),
        ("Open Box SSD", "used"),
        ("Used SAS drive", "used"),
        ("Brand New in box", "new"),
        ("Focused on speed, reused nothing", None),
        ("Avolusion PRO-5X 12TB External Hard Drive", None),
    ],
)
def test_the_first_condition_rule_matching_the_text_names_its_condition(
    text: str, expected: str | None
) -> None:
    assert condition_in(RULES, text) == expected


def test_rule_order_decides_between_texts_that_disagree() -> None:
    # A title saying "Renewed" outranks a condition field saying "New": "renewed" comes first.
    assert condition_in(RULES, "WD Red 4TB (Renewed)", "New") == "refurbished"
    assert condition_in(RULES, None, "Used") == "used"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "Seagate ST1000NM0023 1TB 7200 RPM SAS 6Gb/s 3.5 Inch Enterprise Hard Drive",
            {
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sas",
                "intended_use": ["enterprise"],
            },
        ),
        (
            'MaxDigital 4TB SATA III 6.0Gb/s 3.5" Internal Hard Drive',
            {"media_type": "hdd", "form_factor": "3_5", "interface": "sata"},
        ),
        # Inches written as two apostrophes, as some og:title tags do.
        (
            "MaxDigital 4TB SATA III 6.0Gb/s 3.5'' Internal Hard Drive",
            {"media_type": "hdd", "form_factor": "3_5", "interface": "sata"},
        ),
        (
            "Avolusion PRO-5X 12TB USB 3.0 External Hard Drive",
            {"media_type": "hdd", "interface": "usb"},
        ),
        (
            "Samsung 980 PRO 1TB M.2 NVMe SSD",
            {"media_type": "ssd", "form_factor": "m_2", "interface": "nvme_pcie"},
        ),
        (
            "Crucial MX500 500GB 2.5in SATA Solid State Drive",
            {"media_type": "ssd", "form_factor": "2_5", "interface": "sata"},
        ),
        (
            "SanDisk Extreme 128GB microSDXC card",
            {"media_type": "flash_card", "form_factor": "microsd"},
        ),
        (
            (
                "Seagate Exos ST22000NM000C 22TB 7200RPM SATA 6Gb/s 256MB Cache CMR 3.5-Inch"
                " Enterprise Hard Drive (Certified Refurbished) - 5 Year Warranty"
            ),
            {
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sata",
                "recording_type": "cmr",
                "intended_use": ["enterprise"],
            },
        ),
        ("Mystery storage thing", None),
    ],
)
def test_specifications_in_a_title(title: str, expected: Specs | None) -> None:
    assert specifications_in_title(title) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Seagate IronWolf Pro 12TB CMR NAS Hard Drive", "cmr"),
        ("WD Red 4TB SMR", "smr"),
        ("Toshiba N300 conventional magnetic recording", "cmr"),
        ("Seagate Archive 8TB shingled magnetic recording", "smr"),
        # Said only when the title says so: a WD Red Plus is CMR, but nothing here says it.
        ("WD Red Plus 8TB NAS Hard Drive", None),
        ("CMRX-1 adapter", None),
    ],
)
def test_recording_is_read_only_where_the_text_states_it(text: str, expected: str | None) -> None:
    assert recording_named(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Seagate IronWolf 8TB NAS Hard Drive", ["nas"]),
        ("WD Red Plus 8TB", ["nas"]),
        ("Toshiba N300 6TB", ["nas"]),
        ("Seagate SkyHawk AI 16TB Surveillance", ["surveillance"]),
        ("WD Purple Pro 12TB", ["surveillance"]),
        ("Seagate Exos X18 18TB", ["enterprise"]),
        ("WD Ultrastar DC HC550 18TB", ["enterprise"]),
        ("WD Gold 10TB", ["enterprise"]),
        ("Toshiba MG08ACA16TE 16TB Enterprise Capacity", ["enterprise"]),
        ("Data Center Hard Drive", ["enterprise"]),
        ("Seagate BarraCuda 4TB", ["desktop"]),
        ("WD Blue 2TB", ["desktop"]),
        ("Seagate Archive HDD v2 8TB", ["archive"]),
        ("Seagate IronWolf Pro NAS for enterprise NAS", ["nas", "enterprise"]),
        # "Desktop" alone names an enclosure style, not what the drive is marketed for.
        ("WD Elements Desktop External Hard Drive", []),
        ("Avolusion PRO-5X 12TB USB 3.0 External Hard Drive", []),
    ],
)
def test_intended_use_comes_from_the_makers_product_line_or_stated_use(
    text: str, expected: list[str]
) -> None:
    assert intended_use_named(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Seagate Exos X20 ST18000NM003D 18TB", "Seagate"),
        ("DELL / Seagate Constellation ES.3 ST1000NM0023 1TB", "Seagate"),
        ("Dell / HGST Ultrastar DC HC300 HUS726T4TAL4205 4TB", "Western Digital"),
        ("WD Ultrastar DC HC550 WUH721818ALE6L4 18TB", "Western Digital"),
        ("WD_BLACK™ Gaming Hard Drive - 10TB", "Western Digital"),
        ("Western Digital", "Western Digital"),
        ("Toshiba 14TB MG07 MG07ACA14TEY", "Toshiba"),
        ("Intel D3-S4510 960GB SATA 2.5in SSD", "Intel"),
        ("Samsung 980 PRO 1TB M.2 NVMe SSD", "Samsung"),
        ("Crucial MX500 500GB", "Crucial"),
        ("Kingston A400 240GB", "Kingston"),
        ("SanDisk Extreme 128GB microSDXC", "SanDisk"),
        ("Micron 5300 PRO 960GB", "Micron"),
        ("Avolusion PRO-5X (Grey) 12TB USB 3.0 External Hard Drive", "Avolusion"),
        ("MaxDigital 4TB 7200RPM SATA III", "MaxDigital"),
        ("MDD 12TB 7200RPM SATA", "MaxDigital"),
        ("MaxDigitalData 8TB", "MaxDigital"),
        # OEM labels are not makers; with no maker named, the brand is unknown.
        ("HP 881787-B21 12TB SAS", None),
        ("Dell 0HNHWC 18TB", None),
        ("Mystery storage thing", None),
    ],
)
def test_the_maker_is_named_by_whoever_made_the_drive_not_whoever_relabelled_it(
    text: str, expected: str | None
) -> None:
    assert maker_named(text) == expected
