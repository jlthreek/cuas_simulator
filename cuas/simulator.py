"""
Gray-zone C-UAS 시뮬레이터 — 랜덤 침투체(드론/풍선/새) 궤적 생성 + 센서 관측 모델
"""
import numpy as np

DT = 2.0            # 스텝 간격 (초)
N_STEPS = 40

# 센서 관측 잡음 (도심 클러터 반영)
RADAR_POS_NOISE = 0.04   # km (레이더 위치 정밀)
RF_CEP = 0.42            # km (RF TDOA CEP — 친구 실측 AADM1.csv 중앙값 420m)


def spawn(kind, tid, rng, assets):
    """유형별 물리 프로파일로 궤적 생성. 좌표 km, 속도 m/s."""
    ang = rng.uniform(0, 2 * np.pi)
    r0 = rng.uniform(3.8, 4.8)
    start = np.array([r0 * np.cos(ang), r0 * np.sin(ang)])

    if kind == "drone":
        target = np.array(list(assets.values())[rng.integers(0, len(assets))][:2])
        v = target - start
        v = v / (np.linalg.norm(v) + 1e-9) * rng.uniform(12, 22)   # 자산지향, 능동 빠름
        alt = rng.uniform(60, 180); rcs = rng.uniform(-20, -14); mdop = True
        rf_class = "custom/encrypted" if rng.random() < 0.6 else "commercial"; rf_p = True
    elif kind == "balloon":
        w = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1)])
        w = w / (np.linalg.norm(w) + 1e-9)
        v = w * rng.uniform(3, 7)                                  # 바람종속 느림
        alt = rng.uniform(420, 900); rcs = rng.uniform(-11, -5); mdop = False
        rf_class = "none"; rf_p = False
    else:  # bird
        v = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1)])
        v = v / (np.linalg.norm(v) + 1e-9) * rng.uniform(8, 16)
        alt = rng.uniform(30, 120); rcs = rng.uniform(-26, -20); mdop = False
        rf_class = "none"; rf_p = False

    wind_dir = v / (np.linalg.norm(v) + 1e-9)
    traj = []
    p = start.copy()
    for i in range(N_STEPS):
        p = p + v * DT / 1000.0    # m/s * s -> km
        rf_pos = p + rng.normal(0, RF_CEP, 2) if rf_p else (np.nan, np.nan)
        traj.append(dict(
            t=i * DT, x=float(p[0]), y=float(p[1]), alt=float(alt + rng.normal(0, 6)),
            radar_x=float(p[0] + rng.normal(0, RADAR_POS_NOISE)),
            radar_y=float(p[1] + rng.normal(0, RADAR_POS_NOISE)),
            rf_x=float(rf_pos[0]), rf_y=float(rf_pos[1]),
            rcs=float(rcs + rng.normal(0, 1.5)), mdop=bool(mdop),
            rf_class=rf_class, rf_present=bool(rf_p), snr=float(rng.uniform(6, 20)),
        ))
    return dict(tid=tid, truth=kind, wind_dir=wind_dir.tolist(), traj=traj)


def generate_scenario(n_drone=3, n_balloon=3, n_bird=4, seed=42, assets=None):
    """랜덤 다중 침투 시나리오 생성"""
    from .engine import ASSETS
    assets = assets or ASSETS
    rng = np.random.default_rng(seed)
    mix = ["drone"] * n_drone + ["balloon"] * n_balloon + ["bird"] * n_bird
    rng.shuffle(mix)
    return [spawn(k, f"T{i:02d}", rng, assets) for i, k in enumerate(mix)]
