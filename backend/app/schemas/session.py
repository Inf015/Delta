import uuid
from pydantic import BaseModel


class SessionOut(BaseModel):
    session_id: uuid.UUID
    simulator: str
    track: str
    car: str
    lap_time: float
    lap_time_fmt: str
    s1: float
    s2: float
    s3: float
    tyre_compound: str
    track_length: float
    session_type: str
    lap_number: int
    valid: bool

    model_config = {"from_attributes": True}
