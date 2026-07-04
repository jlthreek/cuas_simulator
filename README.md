# Gray-zone C-UAS 시뮬레이터

도심 상공 저신호(LSS) 침투체(드론·풍선·조류)를 **랜덤 생성 → 탐지·융합 → 분류 → 위협평가 →
대응결심 → 경보 시각화**까지 자동 수행하는 의사결정 지원 시뮬레이터.

## 요구기능 대응

| 요구 | 구현 위치 |
|---|---|
| RF·EO/IR·레이더 융합 저신호 탐지 | `pipeline.fuse_detect()` (SNR 게이트 + RF·레이더 시공간 연관) |
| 도심 클러터 오탐 저감 | `engine.lss_gate()` + 자기운동 보정(`pipeline.run(mobile=True)`) |
| 유형 분류 + 위협도 평가 | `engine.classify()` (위계적) + `engine.assess_threat()` (AHP 가중) |
| 부수피해 대응 추천(soft/hard) | `engine.recommend()` (인구밀도 반영, TOPSIS 근거) |
| 다중 추적 + 경보 시각화 | `dashboard.render()` (상황도+위협전개+경보판) |

## 설치 & 실행

```bash
pip install -r requirements.txt

python run.py                          # 기본(드론3·풍선3·새4)
python run.py --seed 11 --mobile       # 이동형(자기운동 보정)
python run.py --drones 5 --pop-density 0.8   # 구성·인구밀도 변경
python run.py --rf data/AADM1.csv      # 실측 RF(Keysight TDOA) 품질 요약
```

출력: `dashboard.png`(경보 시각화), `simulation_timeline.csv`(스텝별 로그), 콘솔 요약.

## 구조

```
cuas_simulator/
├── run.py              # CLI 진입점
├── requirements.txt
├── data/AADM1.csv      # 실측 RF 샘플 (Keysight RATEL TDOA)
├── train_threat_ml.py  # RADAR/RF 기반 threat_level 사전분류기 학습 CLI
└── cuas/
    ├── engine.py       # 판단로직·임계값 (근거 기반)
    ├── simulator.py    # 랜덤 침투체 궤적 생성 + 센서 관측 모델
    ├── pathfinding.py  # 드론 경로탐색(그리드 A*) — 건물 등 장애물 회피
    ├── pipeline.py     # 스텝별 처리 (융합→분류→위협→대응)
    ├── dashboard.py    # 경보 시각화
    ├── rf_adapter.py   # 실측 RF CSV 어댑터
    └── threat_ml/      # RADAR/RF 관측 기반 threat_level(LOW/MED/HIGH) 사전분류기 (독립 모듈)
```

## RADAR/RF 기반 threat_level 사전분류기 (`cuas/threat_ml/`)

Desktop의 `sensor_threat_classifier`(규칙 기반 사전필터 + 정규화 ML 재분류) 프로젝트를 이식한
독립 모듈. IR/광학 센서는 이 프로젝트에 없으므로 사용하지 않고, `cuas.simulator`/`cuas.pipeline`이
이미 생성하는 RADAR·RF 관측값(RCS, 고도, 속도, 접근속도, 자산거리, 풍향정합, 마이크로도플러,
RF 방사/종류)만으로 학습한다. `engine.py`/`pipeline.py`/`simulator.py`는 감싸서 재사용할 뿐
수정하지 않으며, 라벨(threat_level)은 `engine.recommend()`의 대응옵션(none/soft/hard)을
그대로 LOW/MEDIUM/HIGH로 매핑해 만든다.

- **1단계 규칙**: 로터 마이크로도플러·RF 방사가 모두 없으면 즉시 LOW (원본의 "IR 무열원→LOW"를
  cuas가 보유한 신호로 재구성).
- **2단계 ML**: 남은(추진/RF 신호가 있는) 표적을 LogisticRegression(L2) vs 얕은 RandomForest 중
  교차검증 성능이 좋은 쪽으로 MEDIUM/HIGH 재분류. 같은 트랙의 시점들이 train/val/test에 섞이지
  않도록 트랙 단위(group)로 분할해 시간적 data leakage를 방지.

```bash
python train_threat_ml.py                    # 기본 40개 시나리오로 학습
python train_threat_ml.py --scenarios 80 --seed 7
```

출력: `outputs/threat_ml/confusion_matrix_test.png`, `learning_curve.png`,
`final_classification_result.csv`, `model_bundle.joblib`(추론 재사용, `cuas.threat_ml.predict` 참조).

## 판단로직 근거 (요약)

- **탐지 LSS 게이트**: RCS≤−10dBsm(쿼드)~−18(고정익), 속도<15m/s — Drones 7(1) Art.39; Sensors 19(22) Art.5048
- **분류(위계적)**: 마이크로도플러·RF·RCS·고도·풍향정합. 풍선=로터/RF 부재 & RCS>−12 & 고도>400m
- **위협평가**: T=100·(0.35·근접+0.19·의도+0.35·능력+0.11·NFZ) — AHP 가중(CR=0.004)
- **대응결심**: 위협도 구간 + 부수피해(인구밀도) → soft/hard-kill — Effect-based WTA/TOPSIS

> 임계값은 문헌·표준방법론 기반 초기값이며, 운용 레이더·표적군에 맞춘 재보정이 필요.
> 상세 근거·출처는 상위 프로젝트 문서(`CUAS_근거기반_판단로직_기준치.md`, `CUAS_풍선판별_로직.md`) 참조.

## 드론·풍선(·조류) 서브타입 스펙 (`cuas/simulator.py`)

값 변경 시 이 표도 함께 갱신할 것. 서브타입 값들은 모두 `engine.py`의 분류 임계값
(`RCS_GATE_QUAD/FIXED`, `BALLOON_RCS`, `BALLOON_ALT`)을 정확히 통과/미통과하도록 설계됨 —
임계값 자체는 변경하지 않음.

**드론**

| 항목 | 쿼드콥터 (로터형) | 고정익 | 자폭형(FPV/로이터링 뮤니션) | 회전익(헬기형) |
|---|---|---|---|---|
| 고도 (AGL) | 60–150 m | 120–300 m | 30–100 m | 80–250 m |
| 속도 | 10–18 m/s | 16–26 m/s | 25–45 m/s | 5–15 m/s |
| RCS | 정규분포 μ=−9.75, σ=1.2 dBsm (범위 −13~−6) | 정규분포 μ=−17.62, σ=1.2 dBsm (범위 −21~−14) | 정규분포 μ=−14.0, σ=1.2 dBsm (범위 −18~−10) | 정규분포 μ=−6.0, σ=1.2 dBsm (범위 −10~−3) |
| 마이크로도플러 / RF | 있음 / 항상 존재 (60% custom·encrypted, 40% commercial) | 좌동 | 좌동 | 좌동 |
| 근거 | Drones 2023, DJI Inspire1 실측 RCS(−9.75 dBsm) | Drones 2023, 소형 고정익 실측 RCS(−17.62 dBsm) | 우크라이나전 FPV 공격드론 사례(저고도 지형추종, 최대 ~150km/h≈42m/s급 고속 강하) | Schiebel Camcopter 계열 등 소형 무인헬기 ISR 프로파일(저속 정밀체공, 동체가 커 RCS가 쿼드콥터보다 큼) |
| 비고 | 도심 실비행 고도(60–90m)와 부합 | 은닉 침투 가정상 저고도(스탠드오프 고고도 정찰과는 별개 프로파일) | 종말 단계 급강하 공격 특성상 쿼드콥터보다 고속·저RCS(소형 기체) | 단일/동축 로터 기반이라 쿼드콥터와 마이크로도플러 특성은 다르나, 현재 시뮬레이터는 mdop을 불리언으로만 모델링해 값 자체는 동일(True) |

**풍선**

| 항목 | 오물풍선 | 고고도 미사일 풍선 |
|---|---|---|
| 고도 (AGL) | 3,000–5,000 m | 18,000–20,000 m |
| 속도 | 4–9 m/s (지상풍 종속) | 8–20 m/s (성층권 강풍 반영) |
| RCS | −8~−3 dBsm | −11~−6 dBsm (디코이 RCS 저감 반영) |
| 마이크로도플러 / RF | 없음 / 없음 | 없음 / 없음 |
| 근거 | 2024년 북한 오물풍선 사례(제원 3~5km) | 2023년 고고도 정찰/디코이 풍선 사례(관측 고도 약 60,000ft ≈ 18.3km) |

> 두 풍선 서브타입 모두 `BALLOON_ALT(400m)`·`BALLOON_RCS(-12dBsm)`를 여유 있게 상회하도록
> 설계됨. 400m 안팎을 비행하는 "소형풍선" 부류는 실측 근거를 찾지 못해 제외함.

**조류**

| 항목 | 값 |
|---|---|
| 고도 (AGL) | 30–120 m |
| 속도 | 8–16 m/s |
| RCS | −26~−20 dBsm |
| 근거 | 비둘기 실측 AGL 60–88m, 대다수 도심 조류 150m 이하 비행 |

## 드론 경로탐색 (`cuas/pathfinding.py`)

드론은 스폰 시점에 목표 자산까지 직선이 아닌 **그리드 A\* 경로탐색**으로 웨이포인트를 계산하고,
매 스텝 `pathfinding.advance_along_path()`로 그 웨이포인트를 따라 이동한다(목표 도달 시 정지/체공).

- `simulator.generate_scenario(..., obstacles=None)` / `spawn(..., obstacles=None)`로 건물 등
  장애물 폴리곤(`[[(x1,y1),(x2,y2),...], ...]`, km 좌표)을 주입할 수 있다.
- **`obstacles=None`(기본값)이면 기존과 동일하게 목표 자산으로 직선 비행** — 실제 지도(건물)
  데이터는 다른 프로젝트 병합 후 이 인자로 연결할 예정이라 지금은 폴백 상태로 동작한다.
- 풍선·조류는 목표 지향 비행이 아니라(바람/임의 표류) 경로탐색을 적용하지 않는다.

## Claude Code로 확장하기

이 패키지는 순수 numpy/pandas 엔진이라 그대로 서비스화 가능:
1. `engine.py`/`pipeline.py`를 FastAPI로 감싸 WebSocket 스트리밍
2. `dashboard.py` 대신 React+Leaflet 실시간 지도
3. `rf_adapter.py`처럼 레이더 실데이터 어댑터 추가 (스키마: `data/` 참조)
