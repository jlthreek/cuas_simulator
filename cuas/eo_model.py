"""
EO(전자광학) 카메라 관측 모델 — 합성(synthetic) 데이터 생성.

실제 촬영 영상 없이, Johnson 기준(EO/IR 표적획득 성능모델 — NVESD/ACQUIRE 계열에서
표적 탐지·인식 확률을 예측할 때 널리 쓰는 방법론)의 TTPF(Target Transfer Probability
Function)로 거리에 따른 탐지확률·분류신뢰도·픽셀 상당 크기를 합성한다.
실측 영상 기반 검출기(예: YOLO)를 나중에 연결하려면 observe()의 반환 스키마만 맞추면 된다.

가정(실측 근거는 각 상수 옆 주석 참조):
- EO 카메라는 중앙자산(관저·청사, (0,0))에 고정 설치.
- IFOV(화소당 순간시야각) 0.5mrad — 중배율 C-UAS EO/IR 터렛급 가정치.
- 야간/저조도에는 가시광 EO 특성상 탐지성능이 급격히 저하 (illum 계수로 반영, RADAR/RF와
  달리 EO만 갖는 근본적 한계).
"""
import numpy as np

EO_POS = (0.0, 0.0)     # 카메라 위치 (km) — 중앙자산(관저·청사) 기준
IFOV_MRAD = 0.5         # 화소당 순간시야각(mrad) — 중배율 EO/IR 터렛 가정치
N50_DETECT = 2.0        # px, Johnson 기준 "탐지"(~1 cycle)에 필요한 표적 최소치수 상당 픽셀수
N50_RECOG = 8.0         # px, Johnson 기준 "인식"(~4 cycle)에 필요한 픽셀수 — 분류신뢰도 산출에 사용
TTPF_EXP = 2.7          # TTPF 경험적 지수 (Johnson/NVESD 계열에서 흔히 쓰는 값)


def _ttpf(n_px, n50, exp=TTPF_EXP):
    """Target Transfer Probability Function: n50 픽셀에서 확률 0.5가 되는 S자형 함수"""
    if n_px <= 0:
        return 0.0
    return float(n_px ** exp / (n_px ** exp + n50 ** exp))


def observe(p_xy, size_m, rng, illum=1.0, eo_pos=EO_POS, ifov_mrad=IFOV_MRAD):
    """p_xy: 현재 위치(km). size_m: 표적 특징장(익폭/직경 등, m).
    illum: 조도 계수 0(야간)~1(주간) — 가시광 EO는 조도가 낮을수록 유효 픽셀수가 줄어든다.
    반환: dict(eo_present, eo_bbox_px, eo_conf) — 미탐지 시 bbox/conf는 NaN.
    """
    range_m = float(np.hypot(p_xy[0] - eo_pos[0], p_xy[1] - eo_pos[1])) * 1000.0
    n_px = size_m / (range_m * ifov_mrad * 1e-3) if range_m > 1e-6 else float("inf")
    n_px_eff = n_px * float(np.clip(illum, 0.0, 1.0))

    p_detect = _ttpf(n_px_eff, N50_DETECT)
    if rng.random() >= p_detect:
        return dict(eo_present=False, eo_bbox_px=float("nan"), eo_conf=float("nan"))

    bbox_px = float(max(n_px_eff * rng.normal(1.0, 0.1), 0.0))
    conf = float(np.clip(_ttpf(n_px_eff, N50_RECOG) + rng.normal(0, 0.05), 0.0, 1.0))
    return dict(eo_present=True, eo_bbox_px=bbox_px, eo_conf=conf)
