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
└── cuas/
    ├── engine.py       # 판단로직·임계값 (근거 기반)
    ├── simulator.py    # 랜덤 침투체 궤적 생성 + 센서 관측 모델
    ├── pipeline.py     # 스텝별 처리 (융합→분류→위협→대응)
    ├── dashboard.py    # 경보 시각화
    └── rf_adapter.py   # 실측 RF CSV 어댑터
```

## 판단로직 근거 (요약)

- **탐지 LSS 게이트**: RCS≤−10dBsm(쿼드)~−18(고정익), 속도<15m/s — Drones 7(1) Art.39; Sensors 19(22) Art.5048
- **분류(위계적)**: 마이크로도플러·RF·RCS·고도·풍향정합. 풍선=로터/RF 부재 & RCS>−12 & 고도>400m
- **위협평가**: T=100·(0.35·근접+0.19·의도+0.35·능력+0.11·NFZ) — AHP 가중(CR=0.004)
- **대응결심**: 위협도 구간 + 부수피해(인구밀도) → soft/hard-kill — Effect-based WTA/TOPSIS

> 임계값은 문헌·표준방법론 기반 초기값이며, 운용 레이더·표적군에 맞춘 재보정이 필요.
> 상세 근거·출처는 상위 프로젝트 문서(`CUAS_근거기반_판단로직_기준치.md`, `CUAS_풍선판별_로직.md`) 참조.

## Claude Code로 확장하기

이 패키지는 순수 numpy/pandas 엔진이라 그대로 서비스화 가능:
1. `engine.py`/`pipeline.py`를 FastAPI로 감싸 WebSocket 스트리밍
2. `dashboard.py` 대신 React+Leaflet 실시간 지도
3. `rf_adapter.py`처럼 레이더 실데이터 어댑터 추가 (스키마: `data/` 참조)
