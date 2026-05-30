import json

import numpy as np
from mlserver import MLModel
from mlserver.codecs import decode_args
from mlserver.utils import get_model_uri
from prophet import Prophet
from prophet.serialize import model_from_dict


class ProphetRuntime(MLModel):
    async def load(self) -> bool:
        model_uri = await get_model_uri(
            self._settings, wellknown_filenames=["model.json"]
        )
        with open(model_uri) as f:
            self._model: Prophet = model_from_dict(json.load(f))
        return True

    @decode_args
    async def predict(self, horizon: np.ndarray) -> np.ndarray:
        future = self._model.make_future_dataframe(periods=horizon[0], freq="T")
        forecast = self._model.predict(future)
        return forecast["yhat"].iloc[-1:].to_numpy()
