from typing import Literal

DriveInventoryIssueType0 = Literal['stale', 'unknown_specifications']

DRIVE_INVENTORY_ISSUE_TYPE_0_VALUES: set[DriveInventoryIssueType0] = { 'stale', 'unknown_specifications',  }

def check_drive_inventory_issue_type_0(value: str) -> DriveInventoryIssueType0:
    if value in DRIVE_INVENTORY_ISSUE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {DRIVE_INVENTORY_ISSUE_TYPE_0_VALUES!r}")
