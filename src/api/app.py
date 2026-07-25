from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from src.api.schemas.response import WeatherResponse
from src.domain.exceptions.exceptions import (
    BaseWeatherException,
    InsufficientHistoryException,
    InvalidCityException,
    NoDataException,
)
from src.repositories.config import MODELS_DIR, get_engine
from src.repositories.sqlalchemy_weather_repository import (
    SqlAlchemyWeatherRepository,
)
from src.repositories.xgboost_models_repository import XGBoostModelsRepository
from src.use_cases.prediction import WeatherUseCase

app = FastAPI(title='Weather Forecast')

WEATHER_EXCEPTION_STATUS = {
    InvalidCityException: 404,
    NoDataException: 404,
    InsufficientHistoryException: 422,
}


@app.exception_handler(BaseWeatherException)
def handle_weather_exception(
    request: Request, exc: BaseWeatherException
) -> JSONResponse:
    status_code = WEATHER_EXCEPTION_STATUS.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={'detail': str(exc)})


engine = get_engine()
WR = SqlAlchemyWeatherRepository(engine=engine)
MR = XGBoostModelsRepository(models_dir=str(MODELS_DIR), source='db')


FRONTEND_FILE = (
    Path(__file__).resolve().parents[2] / 'web' / 'WeatherForecast.html'
)


def get_weather_use_case() -> WeatherUseCase:
    return WeatherUseCase(WR, MR)


@app.get('/', include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_FILE)


@app.get('/weather', response_model=WeatherResponse)
def weather(
    city: str,
    time: datetime,
    wus: WeatherUseCase = Depends(get_weather_use_case),  # noqa: B008
) -> WeatherResponse:
    time = wus.to_naive_local(city, time)
    if time <= wus.now_in_city(city):
        points = wus.get_from_archive(city, time)
    else:
        points = wus.predict(city, time)
    return WeatherResponse(
        time=[p.ts for p in points],
        temp=[p.temperature for p in points],
    )
