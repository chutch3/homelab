from typing import Literal

SettingViewType = Literal['flag', 'list', 'text']

SETTING_VIEW_TYPE_VALUES: set[SettingViewType] = { 'flag', 'list', 'text',  }

def check_setting_view_type(value: str) -> SettingViewType:
    if value in SETTING_VIEW_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SETTING_VIEW_TYPE_VALUES!r}")
