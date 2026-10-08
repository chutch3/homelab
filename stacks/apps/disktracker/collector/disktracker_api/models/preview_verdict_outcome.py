from typing import Literal

PreviewVerdictOutcome = Literal['ignored', 'recorded', 'review']

PREVIEW_VERDICT_OUTCOME_VALUES: set[PreviewVerdictOutcome] = { 'ignored', 'recorded', 'review',  }

def check_preview_verdict_outcome(value: str) -> PreviewVerdictOutcome:
    if value in PREVIEW_VERDICT_OUTCOME_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PREVIEW_VERDICT_OUTCOME_VALUES!r}")
