"""
predict.py
----------
학습된 threat_level 사전분류기를 재사용하기 위한 추론 헬퍼
(향후 FastAPI 백엔드에서 실시간 트랙에 적용할 때 사용).

1단계 규칙(추진/RF 신호 없음 -> LOW)을 먼저 적용하고, 해당하지 않으면
train.py가 저장한 모델 번들(스케일러+추정기)로 2단계 판정을 수행한다.
"""
from dataclasses import dataclass
from typing import Any, Dict

import joblib

from .preprocessing import FEATURE_COLUMNS, RF_CLASSES


@dataclass
class ThreatMLBundle:
    scaler: Any
    estimator: Any


def save_bundle(scaler, estimator, path: str) -> None:
    joblib.dump(ThreatMLBundle(scaler=scaler, estimator=estimator), path)


def load_bundle(path: str) -> ThreatMLBundle:
    return joblib.load(path)


def predict_one(bundle: ThreatMLBundle, features: Dict[str, Any]) -> str:
    """features 키: radar_rcs_dbsm, radar_alt_m, radar_speed_mps, radar_closing_kmpm,
    radar_range_km, radar_wind_align, mdop_detected(0/1), rf_present(0/1), rf_class(str)."""
    if not features.get("mdop_detected") and not features.get("rf_present"):
        return "LOW"

    row = dict(features)
    for c in RF_CLASSES:
        row[f"rf_class_{c.replace('/', '_')}"] = int(row.get("rf_class") == c)

    x = [[row[col] for col in FEATURE_COLUMNS]]
    x_scaled = bundle.scaler.transform(x)
    return str(bundle.estimator.predict(x_scaled)[0])
