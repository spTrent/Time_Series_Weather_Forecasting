import joblib
from xgboost import XGBRegressor
import pandas as pd
import os

class XGBoostModelsRepository:
    def __init__(self, models_dir: str, source: str, models_count: int = 7) -> None:
        schema = joblib.load(os.path.join(models_dir, 'feature_schema.joblib'))
        self.feature_columns = schema['feature_columns']
        self._models: dict[int, XGBRegressor] = {}
        self.models_count = models_count

        for day in range(1, models_count + 1):
            model = XGBRegressor()
            model.load_model(os.path.join(models_dir, f'model_day_{day}_with_{source}.json'))
            self._models[day] = model

    def predict(self, day: int, data: pd.DataFrame) -> float:
        model = self._models[day]
        data = data[self.feature_columns]
        return float(model.predict(data)[0])
