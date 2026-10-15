from dataclasses import dataclass


@dataclass(slots=True)
class ServiceContext:
    user_id: str | None = None
    data_center_id: str | None = None
