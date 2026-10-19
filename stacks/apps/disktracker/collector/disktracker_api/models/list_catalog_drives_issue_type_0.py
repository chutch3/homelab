from typing import Literal

ListCatalogDrivesIssueType0 = Literal['stale', 'unknown_specifications']

LIST_CATALOG_DRIVES_ISSUE_TYPE_0_VALUES: set[ListCatalogDrivesIssueType0] = { 'stale', 'unknown_specifications',  }

def check_list_catalog_drives_issue_type_0(value: str) -> ListCatalogDrivesIssueType0:
    if value in LIST_CATALOG_DRIVES_ISSUE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_CATALOG_DRIVES_ISSUE_TYPE_0_VALUES!r}")
