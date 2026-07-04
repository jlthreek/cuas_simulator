# CLAUDE.md — 프로젝트 컨텍스트 (Claude Code 자동 로드)

## 무엇을 만드는가
도심 Gray-zone Counter-UAS 의사결정 지원 **대시보드 프로그램**.
저신호(LSS) 침투체(드론/풍선/조류)를 탐지→추적→식별→위협평가→대응결심까지 지원.
부수피해 최소화가 하드 제약.

## 이미 동작하는 엔진 (건드리지 말고 감싸기)
- `cuas/engine.py` — 판단로직·임계값 (논문 근거 있음, **임의 변경 금지**)
- `cuas/simulator.py` — 랜덤 침투체 궤적 생성
- `cuas/pipeline.py` — 스텝별 처리(융합→분류→위협→대응) + 이동형 자기운동 보정
- `cuas/dashboard.py` — matplotlib 시각화(레퍼런스)
- `cuas/rf_adapter.py` — 실측 RF CSV 어댑터
- `run.py` — CLI (동작 확인: `python run.py --seed 11 --mobile`)

## 개발 목표
1. FastAPI 백엔드로 엔진 래핑 → WebSocket 실시간 스트리밍
2. React+TS 프론트: 지도(트랙·자산·NFZ) + 트랙리스트(위협게이지) + 결심패널(TOPSIS) + 타임라인

## 핵심 규칙
- 임계값(engine.py)은 논문 근거가 있다. 변경은 근거와 함께 **제안만**.
- RF 위치는 부정확(CEP 420m) → 위치는 레이더 주도, RF는 증거로만.
- 좌표계: km 지역좌표(원점=중심자산).

## 엔진 사용 예
```python
from cuas import simulator, pipeline, engine
scen = simulator.generate_scenario(3, 3, 4, seed=42)
rows, final = pipeline.run(scen, mobile=False, pop_density=0.5)
```
