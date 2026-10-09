"""A drive's specifications as plain entered values."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

MediaType = Literal["hdd", "ssd", "flash_card", "unknown"]
FormFactor = Literal["3_5", "2_5", "m_2", "microsd", "sd", "unknown"]
Interface = Literal["sata", "sas", "nvme_pcie", "usb", "unknown"]
Recording = Literal["cmr", "smr", "unknown"]
IntendedUse = Literal["nas", "surveillance", "enterprise", "desktop", "archive"]


class Specifications(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_type: MediaType = "unknown"
    form_factor: FormFactor = "unknown"
    interface: Interface = "unknown"
    recording_type: Recording = "unknown"
    intended_use: list[IntendedUse] = []

    @field_validator("intended_use")
    @classmethod
    def once_each(cls, value: list[IntendedUse]) -> list[IntendedUse]:
        return list(dict.fromkeys(value))
