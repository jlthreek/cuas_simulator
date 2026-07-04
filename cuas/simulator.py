"""
Gray-zone C-UAS 시뮬레이터 — 랜덤 침투체(드론/풍선/새) 궤적 생성 + 센서 관측 모델
"""
import numpy as np
from . import pathfinding

DT = 2.0            # 스텝 간격 (초)
N_STEPS = 40

# 센서 관측 잡음 (도심 클러터 반영)
RADAR_POS_NOISE = 0.04   # km (레이더 위치 정밀)
RF_CEP = 0.42            # km (RF TDOA CEP — 친구 실측 AADM1.csv 중앙값 420m)


def spawn(kind, tid, rng, assets, obstacles=None):
    """유형별 물리 프로파일로 궤적 생성. 좌표 km, 속도 m/s.

    드론/풍선은 내부적으로 서로 다른 실제 제원 근거를 갖는 서브타입으로 세분화한다
    (engine.py 주석 근거: RCS_GATE_QUAD/FIXED — Drones2023 DJI Inspire1/소형고정익 실측치,
    BALLOON_ALT — README 오물풍선 제원 3~5km).

    obstacles: 건물 등 실제 지도 장애물 폴리곤 리스트 (드론에만 적용, pathfinding.plan_path 참조).
    None이면 드론도 기존과 동일하게 목표 자산으로 직선 비행한다.
    """
    ang = rng.uniform(0, 2 * np.pi)
    r0 = rng.uniform(3.8, 4.8)
    start = np.array([r0 * np.cos(ang), r0 * np.sin(ang)])

    waypoints = None   # 드론만 사용 — 경로탐색으로 얻은 웨이포인트(장애물 회피)
    speed = None       # 드론만 사용 — 웨이포인트 추적 시 스칼라 속도(m/s)

    if kind == "drone":
        subtype = str(rng.choice(["쿼드콥터", "고정익", "자폭형(FPV)", "회전익(헬기형)"]))
        target = np.array(list(assets.values())[rng.integers(0, len(assets))][:2])
        v_dir = target - start
        v_dir = v_dir / (np.linalg.norm(v_dir) + 1e-9)
        if subtype == "쿼드콥터":
            speed = rng.uniform(10, 18)                               # 로터형: 저속 정밀기동
            alt = rng.uniform(60, 150)
            rcs = float(np.clip(rng.normal(-9.75, 1.2), -13, -6))    # DJI Inspire1 실측(Drones2023)
        elif subtype == "고정익":
            speed = rng.uniform(16, 26)                               # 고정익: 고속 장거리
            alt = rng.uniform(120, 300)
            rcs = float(np.clip(rng.normal(-17.62, 1.2), -21, -14))  # 소형 고정익 실측(Drones2023)
        elif subtype == "자폭형(FPV)":
            speed = rng.uniform(25, 45)                               # FPV/로이터링 뮤니션: 저고도 고속 강하공격
            alt = rng.uniform(30, 100)
            rcs = float(np.clip(rng.normal(-14.0, 1.2), -18, -10))   # 소형 5인치급 기체(쿼드콥터보다 작음)
        else:  # 회전익(헬기형)
            speed = rng.uniform(5, 15)                                # 단일/동축로터: 저속 정밀체공(ISR)
            alt = rng.uniform(80, 250)
            rcs = float(np.clip(rng.normal(-6.0, 1.2), -10, -3))     # 대형 동체+로터(쿼드콥터보다 RCS 큼)
        mdop = True
        rf_class = "custom/encrypted" if rng.random() < 0.6 else "commercial"; rf_p = True
        waypoints = pathfinding.plan_path(tuple(start), tuple(target), obstacles=obstacles, altitude=alt)
        v = v_dir * speed   # wind_dir(초기 헤딩) 산출용 — 실제 이동은 웨이포인트 추적으로 수행
    elif kind == "balloon":
        subtype = str(rng.choice(["오물풍선", "고고도 미사일 풍선"]))
        w = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1)])
        w = w / (np.linalg.norm(w) + 1e-9)
        if subtype == "오물풍선":                                    # 제원 3~5km 저고도 (README 근거)
            v = w * rng.uniform(4, 9)
            alt = rng.uniform(3000, 5000)
            rcs = rng.uniform(-8, -3)
        else:  # 고고도 미사일 풍선: 성층권 정찰/디코이용 (2023 정찰풍선 사례 ~18~20km 참고)
            v = w * rng.uniform(8, 20)                               # 성층권 강풍 반영, 저고도풍선보다 고속
            alt = rng.uniform(18000, 20000)
            rcs = rng.uniform(-11, -6)                               # 디코이 RCS저감 반영, engine.BALLOON_RCS(-12) 상회 유지
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
    wp_idx = 0
    for i in range(N_STEPS):
        if kind == "drone":
            p, wp_idx = pathfinding.advance_along_path(p, waypoints, wp_idx, speed * DT / 1000.0)
        else:
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


def generate_scenario(n_drone=3, n_balloon=3, n_bird=4, seed=42, assets=None, obstacles=None):
    """랜덤 다중 침투 시나리오 생성.

    obstacles: 건물 등 실제 지도 장애물 폴리곤 리스트 (드론 경로탐색에 사용, pathfinding.plan_path 참조).
    다른 프로젝트의 지도/건물 데이터 병합 후 이 인자로 주입하면 드론이 건물을 피해 비행한다.
    """
    from .engine import ASSETS
    assets = assets or ASSETS
    rng = np.random.default_rng(seed)
    mix = ["drone"] * n_drone + ["balloon"] * n_balloon + ["bird"] * n_bird
    rng.shuffle(mix)
    return [spawn(k, f"T{i:02d}", rng, assets, obstacles=obstacles) for i, k in enumerate(mix)]
