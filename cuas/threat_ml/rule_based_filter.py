"""
rule_based_filter.py
---------------------
원본 sensor_threat_classifier의 'IR 무열원 -> LOW' 결정론적 사전필터를,
cuas 시뮬레이터가 실제로 보유한 신호로 재구성한 버전.

IR 열원 대신 cuas의 능동 위협 신호(로터 마이크로도플러 / RF 방사)를 쓴다:
로터 신호도 RF 방사도 없다면 자력 추진·능동 통신 수단이 없다는 뜻이므로
(engine.classify()도 동일 전제로 새/풍선 후보를 가른다) 통계 모델 없이
즉시 LOW로 확정한다. 이렇게 ML 모델은 추진/RF 신호가 있어 애매한
표적(대부분 드론 후보)의 MEDIUM/HIGH 구분에만 집중한다.
"""
import pandas as pd


def apply_no_propulsion_rule(df: pd.DataFrame) -> pd.DataFrame:
    """pre_classified/pre_reason/stage1_threat_level 컬럼을 추가한다."""
    required = {"mdop_detected", "rf_present"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")

    df = df.copy()
    no_signature = (df["mdop_detected"] == 0) & (df["rf_present"] == 0)
    df["pre_classified"] = no_signature
    df["pre_reason"] = ""
    df.loc[no_signature, "pre_reason"] = (
        "로터 마이크로도플러 및 RF 방사 미검출 -> 능동 추진/통신 신호 없음 "
        "-> 규칙 기반 LOW 확정"
    )
    df["stage1_threat_level"] = None
    df.loc[no_signature, "stage1_threat_level"] = "LOW"
    return df


def split_for_pipeline(df: pd.DataFrame):
    """규칙 적용 후 (규칙 확정 LOW, ML 정밀분류 필요) 두 그룹으로 나눈다."""
    pre_filtered_df = df[df["pre_classified"]].copy()
    needs_ml_df = df[~df["pre_classified"]].copy()
    return pre_filtered_df, needs_ml_df
