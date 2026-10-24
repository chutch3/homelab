from typing import Literal

RunStatus = Literal['abandoned', 'completed', 'failed', 'running', 'stopped']

RUN_STATUS_VALUES: set[RunStatus] = { 'abandoned', 'completed', 'failed', 'running', 'stopped',  }

def check_run_status(value: str) -> RunStatus:
    if value in RUN_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RUN_STATUS_VALUES!r}")
