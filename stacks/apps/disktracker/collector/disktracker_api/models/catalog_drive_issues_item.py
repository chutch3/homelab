from typing import Literal

CatalogDriveIssuesItem = Literal['stale', 'unknown_specifications']

CATALOG_DRIVE_ISSUES_ITEM_VALUES: set[CatalogDriveIssuesItem] = { 'stale', 'unknown_specifications',  }

def check_catalog_drive_issues_item(value: str) -> CatalogDriveIssuesItem:
    if value in CATALOG_DRIVE_ISSUES_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CATALOG_DRIVE_ISSUES_ITEM_VALUES!r}")
