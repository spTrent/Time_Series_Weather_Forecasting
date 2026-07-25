from datetime import datetime

from pydantic import BaseModel


class WeatherResponse(BaseModel):
    time: list[datetime]
    temp: list[float]
