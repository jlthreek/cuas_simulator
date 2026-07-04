#!/usr/bin/env python3
"""
RADAR/RF 기반 threat_level(LOW/MEDIUM/HIGH) 사전분류기 학습 CLI.

원본: Desktop/sensor_threat_classifier 이식 — IR/광학 센서 없이 cuas 시뮬레이터가
실제로 생성하는 RADAR/RF 관측만 사용한다 (cuas/threat_ml/ 참조).
engine.py/pipeline.py/simulator.py는 수정하지 않고 감싸서 사용한다.

사용법:
  python train_threat_ml.py                     # 기본 40개 시나리오로 학습
  python train_threat_ml.py --scenarios 80 --seed 7

출력: outputs/threat_ml/ 아래 confusion_matrix_test.png, learning_curve.png,
      final_classification_result.csv, model_bundle.joblib
"""
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cuas.threat_ml.train import _cli

if __name__ == "__main__":
    _cli()
