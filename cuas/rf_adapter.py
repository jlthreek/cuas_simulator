"""
실측 RF 데이터 어댑터 — Keysight RATEL TDOA CSV (예: AADM1.csv)
주의: 이 CSV는 후행 콤마로 컬럼이 밀릴 수 있어 index_col=False 필수.
"""
import numpy as np
import pandas as pd


def load_rf_csv(path):
    """RF TDOA CSV 로드 → 유효 위치추정만 정제해 반환"""
    df = pd.read_csv(path, index_col=False)
    df.columns = [c.strip() for c in df.columns]
    for c in ["Latitude", "Longitude", "CEP", "RHO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    valid = df[(df["Latitude"].abs() > 1e-3) & (df["Longitude"].abs() > 1e-3)].copy()
    valid["low_confidence"] = valid["CEP"] > 500     # CEP>500m는 저신뢰 플래그
    valid["freq_ghz"] = df["Center Frequency"] / 1e9
    return valid


def summarize(valid, total=None):
    """RF 측위 품질 요약 (CEP·주파수·유효율)"""
    return dict(
        valid_fixes=int(len(valid)),
        total=int(total) if total else None,
        center_freq_ghz=float(valid["freq_ghz"].median()) if len(valid) else None,
        cep_median_m=float(valid["CEP"].median()) if len(valid) else None,
        cep_max_m=float(valid["CEP"].max()) if len(valid) else None,
        low_conf_ratio=float(valid["low_confidence"].mean()) if len(valid) else None,
    )


if __name__ == "__main__":
    import sys
    v = load_rf_csv(sys.argv[1])
    print(summarize(v))
