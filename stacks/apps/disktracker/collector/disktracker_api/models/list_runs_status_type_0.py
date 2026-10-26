from typing import Literal

ListRunsStatusType0 = Literal['abandoned', 'completed', 'failed', 'running', 'stopped']

LIST_RUNS_STATUS_TYPE_0_VALUES: set[ListRunsStatusType0] = { 'abandoned', 'completed', 'failed', 'running', 'stopped',  }

def check_list_runs_status_type_0(value: str) -> ListRunsStatusType0:
    if value in LIST_RUNS_STATUS_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_RUNS_STATUS_TYPE_0_VALUES!r}")
