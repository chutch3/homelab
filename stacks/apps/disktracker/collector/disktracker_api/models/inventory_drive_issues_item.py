from typing import Literal

InventoryDriveIssuesItem = Literal['stale', 'unknown_specifications']

INVENTORY_DRIVE_ISSUES_ITEM_VALUES: set[InventoryDriveIssuesItem] = { 'stale', 'unknown_specifications',  }

def check_inventory_drive_issues_item(value: str) -> InventoryDriveIssuesItem:
    if value in INVENTORY_DRIVE_ISSUES_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INVENTORY_DRIVE_ISSUES_ITEM_VALUES!r}")
