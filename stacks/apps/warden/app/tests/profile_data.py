"""Static Arr API and portable-catalog contract examples."""

REMOTE_PROFILE = {
    "id": 45, "name": "HD", "upgradeAllowed": True, "cutoff": 1000,
    "minFormatScore": 0, "cutoffFormatScore": 1000, "minUpgradeFormatScore": 1,
    "language": {"id": -2, "name": "Original"},
    "items": [
        {"id": 1, "quality": {"id": 1, "name": "SDTV"}, "allowed": False, "items": []},
        {"id": 1000, "name": "WEB 1080p", "allowed": True, "items": [
            {"quality": {"id": 3, "name": "WEBDL-1080p"}, "allowed": True, "items": []},
            {"quality": {"id": 15, "name": "WEBRip-1080p"}, "allowed": True, "items": []},
        ]},
    ],
    "formatItems": [{"format": 17, "name": "Preferred", "score": 100}],
}


REMOTE_FORMAT = {
    "id": 17, "name": "Preferred", "includeCustomFormatWhenRenaming": False,
    "specifications": [{
        "name": "Preferred release", "implementation": "ReleaseTitleSpecification",
        "negate": False, "required": True,
        "fields": [{"name": "value", "value": "Preferred", "label": "Regular Expression", "type": "textbox"}],
    }],
}


PROFILE = """schema_version: 1
quality_profiles:
  - name: HD
    upgrade:
      allowed: true
      until_quality: WEB 1080p
      until_score: 1000
    min_format_score: 0
    min_upgrade_format_score: 1
    qualities:
      - name: WEB 1080p
        qualities: [WEBDL-1080p, WEBRip-1080p]
    custom_format_scores:
      Preferred: 100
"""


CUSTOM_FORMAT = {
    "name": "Preferred",
    "includeCustomFormatWhenRenaming": False,
    "specifications": [{
        "name": "Preferred release", "implementation": "ReleaseTitleSpecification",
        "negate": False, "required": True,
        "fields": [{"name": "value", "value": "\\bPreferred\\b"}],
    }],
}
