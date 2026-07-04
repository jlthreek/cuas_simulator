#!/usr/bin/env python3
"""
Gray-zone C-UAS 시뮬레이터 CLI

사용법:
  python run.py                          # 기본 시나리오 (드론3 풍선3 새4)
  python run.py --seed 11 --mobile       # 이동형(자기운동 보정) 모드
  python run.py --drones 5 --balloons 2  # 구성 변경
  python run.py --rf data/AADM1.csv      # 실측 RF 데이터 품질 요약 출력

출력: dashboard.png (경보 시각화) + simulation_timeline.csv + 콘솔 요약
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from cuas import simulator, pipeline, dashboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--drones", type=int, default=5)
    ap.add_argument("--balloons", type=int, default=5)
    ap.add_argument("--birds", type=int, default=10)
    ap.add_argument("--mobile", action="store_true", help="이동형(자기운동 보정)")
    ap.add_argument("--platform-speed", type=float, default=8.0)
    ap.add_argument("--pop-density", type=float, default=0.5, help="인구밀도 0~1 (부수피해)")
    ap.add_argument("--rf", type=str, default=None, help="실측 RF CSV 품질 요약")
    ap.add_argument("--out", type=str, default="dashboard.png")
    args = ap.parse_args()

    if args.rf:
        from cuas import rf_adapter
        v = rf_adapter.load_rf_csv(args.rf)
        print("[RF 실측 요약]", json.dumps(rf_adapter.summarize(v), ensure_ascii=False, indent=1))
        return

    scen = simulator.generate_scenario(args.drones, args.balloons, args.birds, seed=args.seed)
    rows, final = pipeline.run(scen, mobile=args.mobile,
                               platform_speed=args.platform_speed, pop_density=args.pop_density)
    acc = pipeline.accuracy(final)

    print(f"침투체 {len(scen)}개 | 모드: {'이동형' if args.mobile else '고정형'} | 분류정확도 {acc*100:.0f}%")
    fin = pd.DataFrame(final).T.sort_values("threat", ascending=False)
    print(fin[["truth", "subtype", "pred", "threat", "reco", "kill"]].to_string())

    pd.DataFrame(rows).to_csv("simulation_timeline.csv", index=False)
    dashboard.render(scen, rows, final, args.out)
    print(f"\n저장: {args.out}, simulation_timeline.csv")


if __name__ == "__main__":
    main()
