"""What every model of the API's contract is: one whose published schema says which fields are
always there. What the API answers with always has its defaults filled in, so they are required in
the schema of what it answers; what it is sent may leave them out. A model both sent and answered
with is published once for each."""

from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
