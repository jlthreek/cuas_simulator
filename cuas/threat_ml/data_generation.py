"""
data_generation.py
-------------------
cuas.simulator로 다수 시나리오를 돌려 RADAR/RF 관측 기반 학습 데이터셋을 만든다.
새로운 센서(IR/광학)는 추가하지 않고, cuas.pipeline이 매 스텝 계산하는 것과 동일한
방식으로 특징을 추출한다 (fuse_detect/track_speed/wind_alignment 재사용).

라벨(threat_level)은 engine.assess_threat()이 산출한 위협도(T)를
engine.recommend(T, ttype, pop_density=0.0)의 kill 값(none/soft/hard)으로 역추출해
LOW/MEDIUM/HIGH에 매핑한다. pop_density=0.0으로 고정하는 이유는 고위협 구간에서
포획/요격을 가르는 부수피해(정책) 요인을 배제하고 순수 위협도 구간만 얻기 위함이다.
engine.py의 수치 임계값(45/70 등)은 직접 참조하지 않으므로, 근거가 갱신되어
engine.py가 바뀌어도 이 라벨링은 자동으로 최신 기준을 따른다.
"""
from typing import Optional
import numpy as np
import pandas as pd

from .. import engine, simulator, pipeline

_KILL_TO_LEVEL = {"none": "LOW", "soft": "MEDIUM", "hard": "HIGH"}


def _extract_track_features(tgt: dict, dt_min: float) -> list:
    records = []
    traj = tgt["traj"]
    for step in range(len(traj)):
        obs = traj[step]
        confirmed, pos, _rf_assoc = pipeline.fuse_detect(obs)
        if not confirmed:
            continue

        hist = traj[:step + 1]
        speed = pipeline.track_speed(hist)
        rcs = float(np.median([o["rcs"] for o in hist]))
        alt = float(np.median([o["alt"] for o in hist]))
        mdop = any(o["mdop"] for o in hist)
        rf_p = any(o["rf_present"] for o in hist)
        rf_cls = ("custom/encrypted" if any(o["rf_class"] == "custom/encrypted" for o in hist)
                  else obs["rf_class"])
        wa = pipeline.wind_alignment(hist, tgt["wind_dir"])

        ttype, p_uav = engine.classify(rcs, alt, mdop, rf_p, rf_cls, wa)
        prev = (traj[step - 1]["radar_x"], traj[step - 1]["radar_y"]) if step > 0 else None
        T, d = engine.assess_threat(pos[0], pos[1], ttype, p_uav, prev, dt_min)

        closing_kmpm = 0.0
        if prev is not None:
            closing_kmpm = (engine.dist_to_asset(*prev) - d) / dt_min

        resp = engine.recommend(T, ttype, pop_density=0.0)
        level = _KILL_TO_LEVEL[resp["kill"]]

        records.append(dict(
            radar_rcs_dbsm=rcs,
            radar_alt_m=alt,
            radar_speed_mps=speed,
            radar_closing_kmpm=closing_kmpm,
            radar_range_km=d,
            radar_wind_align=wa,
            mdop_detected=int(mdop),
            rf_present=int(rf_p),
            rf_class=rf_cls,
            truth=tgt["truth"],
            threat_level=level,
            group_id=tgt["tid"],
        ))
    return records


def build_dataset(n_scenarios: int = 40, base_seed: int = 42,
                   assets: Optional[dict] = None) -> pd.DataFrame:
    """cuas.simulator로 n_scenarios개 시나리오를 생성해 RADAR/RF 관측 데이터셋을 만든다."""
    dt_min = simulator.DT / 60.0
    rows = []
    for i in range(n_scenarios):
        seed = base_seed + i
        scenario = simulator.generate_scenario(seed=seed, assets=assets)
        for tgt in scenario:
            for rec in _extract_track_features(tgt, dt_min):
                rec["group_id"] = f"s{seed}_{rec['group_id']}"
                rows.append(rec)
    return pd.DataFrame(rows)
