from typing import Literal

ScrapedResultStatus = Literal['ignored', 'queued', 'recorded']

SCRAPED_RESULT_STATUS_VALUES: set[ScrapedResultStatus] = { 'ignored', 'queued', 'recorded',  }

def check_scraped_result_status(value: str) -> ScrapedResultStatus:
    if value in SCRAPED_RESULT_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SCRAPED_RESULT_STATUS_VALUES!r}")
