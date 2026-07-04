"""
preprocessing.py
-----------------
ML 정밀분류(2단계) 대상(추진/RF 신호가 있는 표적) 특징 전처리.

cuas 데이터는 한 트랙의 여러 시점(step)이 서로 강하게 상관된 시계열이므로,
행(row) 단위로 무작위 분할하면 같은 트랙이 train/val/test에 걸쳐 섞여
시간적 data leakage가 생긴다. 이를 막기 위해 group_id(트랙 단위)로 분할한다.
스케일러는 원본과 동일하게 Train 그룹 기준으로만 fit한다.
"""
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

LABEL_COLUMN = "threat_level"
GROUP_COLUMN = "group_id"

RF_CLASSES = ["commercial", "custom/encrypted"]  # "none"은 기준값이라 컬럼 생략

FEATURE_COLUMNS: List[str] = [
    "radar_rcs_dbsm",
    "radar_alt_m",
    "radar_speed_mps",
    "radar_closing_kmpm",
    "radar_range_km",
    "radar_wind_align",
    "rf_present",
] + [f"rf_class_{c.replace('/', '_')}" for c in RF_CLASSES]


def encode_rf_class(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in RF_CLASSES:
        df[f"rf_class_{c.replace('/', '_')}"] = (df["rf_class"] == c).astype(int)
    return df


def _group_split(groups: np.ndarray, val_size: float, test_size: float, seed: int):
    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    n = len(uniq)
    n_test = max(1, round(n * test_size))
    n_val = max(1, round(n * val_size))
    test_g = uniq[:n_test]
    val_g = uniq[n_test:n_test + n_val]
    train_g = uniq[n_test + n_val:]
    return set(train_g), set(val_g), set(test_g)


def make_splits(df: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.2,
                 seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """트랙(group_id) 단위 분할: train / val / test."""
    train_g, val_g, test_g = _group_split(df[GROUP_COLUMN].to_numpy(), val_size, test_size, seed)
    train = df[df[GROUP_COLUMN].isin(train_g)].reset_index(drop=True)
    val = df[df[GROUP_COLUMN].isin(val_g)].reset_index(drop=True)
    test = df[df[GROUP_COLUMN].isin(test_g)].reset_index(drop=True)
    return train, val, test


def fit_scaler(train_df: pd.DataFrame) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(train_df[FEATURE_COLUMNS])
    return scaler


def transform_features(df: pd.DataFrame, scaler: StandardScaler):
    return scaler.transform(df[FEATURE_COLUMNS])
