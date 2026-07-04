# Claude Code 핸드오프 패키지 — Gray-zone C-UAS 대시보드 개발

이 문서 하나로 Claude Code에서 개발을 시작할 수 있다. 3부 구성:
**① 붙여넣을 프롬프트 · ② 첨부할 자료 · ③ 개발 스펙(참조용)**

---

## ① Claude Code에 붙여넣을 프롬프트

> 아래 블록을 그대로 복사해 Claude Code 첫 메시지로 붙여넣으세요. `cuas_simulator.zip`을 먼저 프로젝트 폴더에 풀어두면 됩니다.

```
너는 도심 Gray-zone Counter-UAS(대드론) 의사결정 지원 시스템을 개발하는 시니어 풀스택 엔지니어다.

[배경]
인구 밀집 도심 상공의 저신호(LSS: 저고도·저속·저RCS) 침투체 — 소형 드론, 침투/오물 풍선, 조류 오탐 —
를 탐지→추적→식별→위협평가→대응결심까지 지원하는 대시보드형 프로그램을 만든다.
부수피해(collateral damage) 최소화가 하드 제약이다.

[이미 있는 것 — 프로젝트 폴더의 cuas_simulator/]
- cuas/engine.py    : 판단로직·근거기반 임계값 (LSS게이트, 위계적 분류, AHP 위협평가, TOPSIS 대응추천)
- cuas/simulator.py : 랜덤 침투체(드론/풍선/새) 궤적 생성 + 센서 관측 모델
- cuas/pipeline.py  : 스텝별 처리 (융합탐지→분류→위협→대응) + 자기운동 보정(이동형)
- cuas/dashboard.py : matplotlib 정적 시각화 (레퍼런스용)
- cuas/rf_adapter.py: 실측 RF CSV(Keysight TDOA) 어댑터
- run.py            : CLI. `python run.py --seed 11 --mobile` 로 동작 확인됨(분류정확도 100%)
- data/AADM1.csv    : 실측 RF 샘플 / data/radar_sample_proper.json : 레이더 트랙 스키마

[목표: 이 엔진을 실사용 대시보드 프로그램으로 확장]
1. 백엔드(FastAPI): cuas 엔진을 감싸 WebSocket으로 트랙+위협도+대응권고를 실시간 스트리밍.
   - GET /api/scenario : 시나리오 생성 파라미터(드론/풍선/새 수, seed, mobile, pop_density)
   - WS  /ws/live      : 매 틱마다 전체 트랙 상태 push (id, type, pos, threat, reco, kill)
   - POST /api/upload_rf : 실측 RF CSV 업로드 → rf_adapter로 품질검증 결과 반환
2. 프론트(React + Vite + TypeScript):
   - 지도 패널(Leaflet 또는 deck.gl): 트랙 아이콘(유형별 색), 방호자산, NFZ 원, 궤적 꼬리, RF발신원 CEP원
   - 트랙 리스트: 위협도 게이지 + 골든타임 카운트다운, 위협도순 정렬
   - 결심 패널: 선택 트랙의 TOPSIS 대응옵션 랭킹 + soft/hard-kill 권고 + 부수피해 표시
   - 위협도 타임라인 차트(recharts)
   - 경보 배너: 위협도 70+ 트랙 발생 시 상단 경고
3. 엔진 로직·임계값은 절대 임의로 바꾸지 말 것. engine.py의 값은 논문 근거가 있다
   (근거는 CUAS_근거기반_판단로직_기준치.md 참조). 변경이 필요하면 근거와 함께 제안만 할 것.

[작업 순서]
1) cuas_simulator.zip 구조 파악 후 python run.py 로 엔진 동작 재현
2) FastAPI 백엔드 스캐폴딩 → 엔진 래핑 → WebSocket 스트리밍
3) React 프론트 스캐폴딩 → 지도 → 트랙리스트 → 결심패널 순
4) 실측 RF 업로드 연동
5) README에 실행법(docker-compose 포함) 정리

먼저 zip 구조를 분석하고 개발 계획을 제시한 뒤 진행해줘.
```

---

## ② Claude Code에 첨부/제공할 자료

### 필수 (코드 + 실행)
| 파일 | 역할 | 아티팩트 |
|---|---|---|
| **cuas_simulator.zip** | 동작하는 엔진·시뮬레이터 전체 (이걸 풀어서 시작) | `e723e58e` |
| AADM1.csv | 실측 RF 샘플 (Keysight TDOA) | `8bd32f9f` |
| radar_sample_proper.json | 레이더 트랙 스키마 | `9c9dc6cf` |
| fused_sample.csv | 융합 데이터셋 포맷 | `e493d23e` |

### 근거·스펙 문서 (Claude Code가 로직 이해에 참조)
| 파일 | 내용 | 아티팩트 |
|---|---|---|
| **CUAS_최종로직_및_개발가이드.md** | 즉시개발 7단계 + 노드별 임계값 | `4b698c04` |
| CUAS_근거기반_판단로직_기준치.md | 임계값·가중치의 논문 근거 (변경 금지 이유) | `81edca21` |
| CUAS_풍선판별_로직.md | 드론/풍선/새 위계적 판별 상세 | `90730b59` |
| CUAS_이동형_C-UAS.md | 이동형 자기운동 보정 | `6b673f4f` |
| CUAS_개발설계서.md | 9계층 아키텍처·기술스택·리포지토리 구조 | `a3ae5426` |
| CUAS_파이프라인_상세.md | 단계별 기법 카탈로그 | `45dfa1c3` |

### 시각 레퍼런스 (UI 디자인 참고)
| 파일 | 내용 | 아티팩트 |
|---|---|---|
| fig5_simulator_dashboard.png | 목표 대시보드 레이아웃 (상황도+위협전개+경보판) | `2616f7a3` |
| fig4_logic_flowchart.png | 전체 판단 로직 플로차트 | `43f35d65` |
| fig3_system_architecture.png | 9계층 시스템 아키텍처 | `f5778495` |

> **팁**: Claude Code에는 `cuas_simulator.zip` + 위 3개 md(최종로직·근거기반·개발설계서) + fig5 이미지만
> 첨부해도 충분합니다. 나머지는 필요 시 추가.

---

## ③ 개발 스펙 (참조용 요약)

### 데이터 계약 (WebSocket 틱 메시지)
```json
{
  "t": 24.0,
  "tracks": [
    {"id":"T03","type":"드론","x":-1.8,"y":2.3,"alt":120,
     "threat":90.7,"d_asset":0.45,"reco":"물리 요격(최후수단)","kill":"hard",
     "p_uav":0.95,"golden_time_s":38}
  ],
  "alerts": [{"id":"T03","level":"critical","msg":"자산 근접 고위협 드론"}]
}
```

### 엔진 API (Claude Code가 감쌀 함수)
```python
from cuas import simulator, pipeline, engine
scen = simulator.generate_scenario(n_drone=3, n_balloon=3, n_bird=4, seed=42)
rows, final = pipeline.run(scen, mobile=False, pop_density=0.5)
# engine.classify(), engine.assess_threat(), engine.recommend() 를 실시간 틱마다 호출
```

### 핵심 임계값 (engine.py — 근거 있음, 변경 금지)
- LSS 게이트: RCS≤−10dBsm(쿼드)~−18(고정익), 속도<15m/s
- 풍선 판정: 로터·RF 부재 & RCS>−12dBsm & 고도>400m & 풍향정합>0.5
- 위협도: T=100·(0.35·근접+0.19·의도+0.35·능력+0.11·NFZ) [AHP CR=0.004]
- 대응: T<45 감시 / 45~70 비살상(재밍·포획) / 70+ 요격(단, 인구밀집이면 포획으로 강등)

### 권장 기술스택
- 백엔드: FastAPI + uvicorn + websockets, 엔진은 순수 numpy(그대로 import)
- 프론트: React + Vite + TypeScript, 지도 Leaflet(간단) 또는 deck.gl(고급), 차트 recharts
- 배포: docker-compose (backend + frontend 2컨테이너)

### 주의사항
- RF 단독 위치는 CEP 중앙값 420m로 부정확(실측 AADM1.csv 확인) → 위치는 레이더 주도, RF는 존재·대역 증거로만.
- 친구 radar_data_sample.json은 빈 에러 응답이라 사용 불가 → radar_sample_proper.json 스키마 사용.
- 좌표계: km 단위 지역좌표(원점=중심자산). 실지도 연동 시 자산 GPS 기준 오프셋 변환 필요.
- 한글 폰트: matplotlib은 Apple SD Gothic Neo / NanumGothic 필요(dashboard.py에 처리됨).
