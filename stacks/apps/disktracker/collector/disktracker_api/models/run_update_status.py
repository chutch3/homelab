from typing import Literal

RunUpdateStatus = Literal['completed', 'failed', 'running', 'stopped']

RUN_UPDATE_STATUS_VALUES: set[RunUpdateStatus] = { 'completed', 'failed', 'running', 'stopped',  }

def check_run_update_status(value: str) -> RunUpdateStatus:
    if value in RUN_UPDATE_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RUN_UPDATE_STATUS_VALUES!r}")
