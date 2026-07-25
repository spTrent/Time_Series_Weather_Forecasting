from typing import Protocol
import pandas as pd

class ModelsRepository(Protocol):
    feature_columns: list[str]
    models_count: int

    def predict(self, day: int, data: pd.DataFrame) -> float:
        ...