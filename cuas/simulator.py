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
    """유형별 물리 프로파일로 궤적 생성. 좌표 km, 속도 m/s.

    드론/풍선은 내부적으로 서로 다른 실제 제원 근거를 갖는 서브타입으로 세분화한다
    (engine.py 주석 근거: RCS_GATE_QUAD/FIXED — Drones2023 DJI Inspire1/소형고정익 실측치,
    BALLOON_ALT — README 오물풍선 제원 3~5km).
    """
    ang = rng.uniform(0, 2 * np.pi)
    r0 = rng.uniform(3.8, 4.8)
    start = np.array([r0 * np.cos(ang), r0 * np.sin(ang)])

    if kind == "drone":
        subtype = str(rng.choice(["쿼드콥터", "고정익"]))
        target = np.array(list(assets.values())[rng.integers(0, len(assets))][:2])
        v_dir = target - start
        v_dir = v_dir / (np.linalg.norm(v_dir) + 1e-9)
        if subtype == "쿼드콥터":
            v = v_dir * rng.uniform(10, 18)                          # 로터형: 저속 정밀기동
            alt = rng.uniform(60, 150)
            rcs = float(np.clip(rng.normal(-9.75, 1.2), -13, -6))    # DJI Inspire1 실측(Drones2023)
        else:  # 고정익
            v = v_dir * rng.uniform(16, 26)                          # 고정익: 고속 장거리
            alt = rng.uniform(120, 300)
            rcs = float(np.clip(rng.normal(-17.62, 1.2), -21, -14))  # 소형 고정익 실측(Drones2023)
        mdop = True
        rf_class = "custom/encrypted" if rng.random() < 0.6 else "commercial"; rf_p = True
    elif kind == "balloon":
        subtype = str(rng.choice(["소형풍선", "대형/오물풍선"]))
        w = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1)])
        w = w / (np.linalg.norm(w) + 1e-9)
        if subtype == "소형풍선":
            v = w * rng.uniform(3, 7)                                # 바람종속 느림
            alt = rng.uniform(420, 900)
            rcs = rng.uniform(-11, -8)                               # engine.BALLOON_RCS(-12) 상회 유지
        else:  # 대형/오물풍선 (제원 3~5km 고고도)
            v = w * rng.uniform(4, 9)
            alt = rng.uniform(3000, 5000)
            rcs = rng.uniform(-8, -3)
        mdop = False
        rf_class = "none"; rf_p = False
    else:  # bird
        subtype = "조류"
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
    return dict(tid=tid, truth=kind, subtype=subtype, wind_dir=wind_dir.tolist(), traj=traj)


def generate_scenario(n_drone=3, n_balloon=3, n_bird=4, seed=42, assets=None):
    """랜덤 다중 침투 시나리오 생성"""
    from .engine import ASSETS
    assets = assets or ASSETS
    rng = np.random.default_rng(seed)
    mix = ["drone"] * n_drone + ["balloon"] * n_balloon + ["bird"] * n_bird
    rng.shuffle(mix)
    return [spawn(k, f"T{i:02d}", rng, assets) for i, k in enumerate(mix)]
