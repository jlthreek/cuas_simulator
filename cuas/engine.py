"""
Gray-zone C-UAS 의사결정 엔진 (순수 numpy, 근거 기반 임계값)
- 탐지(LSS 게이트) → 분류(드론/풍선/새) → 위협평가(AHP 가중) → 대응결심(TOPSIS/부수피해)
근거: Sensors 19(22) Art.5048, Drones 7(1) Art.39, AHP(ISAHP2014), Effect-based WTA
"""
import numpy as np

# ---- 방호자산·공역 설정 (km 좌표계, 원점=중심자산) ----
NFZ_R = 3.0
ASSETS = {
    "관저·청사": (0.0, 0.0, 0.35),
    "발전소":    (2.5, 1.0, 0.30),
    "공항접근로": (-2.0, 2.5, 0.50),
}

# ---- AHP로 도출된 위협 가중치 (CR=0.004, 근거: ahp_weights.csv) ----
W_PROX, W_INTENT, W_CAP, W_NFZ = 0.35, 0.19, 0.35, 0.11

# ---- 근거 기반 임계값 ----
RCS_GATE_QUAD = -10.0     # 상용 쿼드콥터 경계 (Drones2023: DJI Inspire1 -9.75 dBsm)
RCS_GATE_FIXED = -18.0    # 소형 고정익 (Drones2023: -17.62 dBsm)
SPEED_GATE = 15.0         # LSS 저속 게이트 (m/s)
BALLOON_RCS = -12.0       # 풍선 대RCS 임계 (부피체)
BALLOON_ALT = 400.0       # 풍선 고고도 임계 (m) — 오물풍선 제원 3~5km 기반
WIND_ALIGN = 0.5          # 풍향 정합 임계


def dist_to_asset(x, y):
    """가장 가까운 방호자산까지 거리 (km)"""
    return min(np.hypot(x - ax, y - ay) for ax, ay, _ in ASSETS.values())


def in_nfz(x, y):
    return dist_to_asset(x, y) < NFZ_R


def lss_gate(rcs_dbsm, speed_ms):
    """① 탐지: 저신호(LSS) 후보 게이트"""
    low_rcs = rcs_dbsm <= RCS_GATE_QUAD
    low_speed = speed_ms < SPEED_GATE
    # 저RCS(고정익급)는 속도 무관하게 통과
    return low_rcs and (low_speed or rcs_dbsm < RCS_GATE_FIXED)


def classify(rcs_dbsm, alt_m, micro_doppler, rf_present, rf_class, wind_align=0.0):
    """② 식별: 위계적 분류 (드론/풍선/새).
    반환: (유형, p_uav)
    """
    rf_enc = rf_present and rf_class == "custom/encrypted"
    # 능동체(로터/암호RF) → 드론
    if micro_doppler or rf_enc:
        return "드론", 0.95
    # 로터·RF 부재 → 풍선/새 후보
    if not micro_doppler and not rf_present:
        # 풍선 고유: 대RCS + 고고도 (+ 풍향정합 보조)
        if rcs_dbsm > BALLOON_RCS and alt_m > BALLOON_ALT:
            return "풍선", 0.15
        # 새: 소형·저고도
        return "새/기타", 0.10
    # RF는 있으나 비암호(상용) → 드론 가능성
    if rf_present:
        return "드론", 0.80
    return "미상", 0.50


def assess_threat(x, y, ttype, p_uav, prev_xy, dt_min):
    """④ 위협평가: AHP 가중 스코어 (0~100)"""
    d = dist_to_asset(x, y)
    prox = np.clip(1 - d / NFZ_R, 0, 1) ** 0.7
    if prev_xy is not None and dt_min > 0:
        closing = (dist_to_asset(*prev_xy) - d) / dt_min   # km/min, +면 접근
    else:
        closing = 0.0
    intent = np.clip(closing / 0.3, 0, 1)
    cap = min(0.85 * p_uav + (0.3 if ttype == "드론" else 0.1), 1.0)
    nfz = 1.0 if in_nfz(x, y) else 0.0
    T = 100 * (W_PROX * prox + W_INTENT * intent + W_CAP * cap + W_NFZ * nfz)
    return round(float(T), 1), round(float(d), 2)


# ---- 대응옵션 (부수피해 고려, TOPSIS 랭킹 근거) ----
RESPONSES = {
    "감시":   {"label": "감시 지속",              "kill": "none", "collateral": 0.02},
    "재밍":   {"label": "RF 재밍",               "kill": "soft", "collateral": 0.20},
    "포획":   {"label": "포획·유도 회수",         "kill": "soft", "collateral": 0.10},
    "요격":   {"label": "물리 요격(최후수단)",    "kill": "hard", "collateral": 0.85},
}


def recommend(T, ttype, pop_density=0.5):
    """⑤ 대응결심: 위협도 + 부수피해(인구밀도) 고려한 옵션 추천"""
    if T < 45:
        return RESPONSES["감시"]
    if T < 70:
        # 비살상 우선: 드론은 재밍, 그 외(풍선)는 포획
        return RESPONSES["재밍"] if ttype == "드론" else RESPONSES["포획"]
    # 고위협: 인구밀집(부수피해 큼)이면 하드킬 회피 → 포획, 저밀도면 요격 허용
    if pop_density > 0.6:
        return RESPONSES["포획"]
    return RESPONSES["요격"]
