from typing import Literal

ObservationProvenance = Literal['collected', 'manual']

OBSERVATION_PROVENANCE_VALUES: set[ObservationProvenance] = { 'collected', 'manual',  }

def check_observation_provenance(value: str) -> ObservationProvenance:
    if value in OBSERVATION_PROVENANCE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OBSERVATION_PROVENANCE_VALUES!r}")
