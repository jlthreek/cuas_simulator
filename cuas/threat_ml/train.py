"""
train.py
--------
독립 실행형 학습 파이프라인. cuas 시뮬레이터가 생성하는 RADAR/RF 관측만으로
threat_level(LOW/MEDIUM/HIGH) 사전분류기를 학습/평가한다.

engine.py/pipeline.py/simulator.py는 감싸서 사용할 뿐 수정하지 않는다
(라벨은 engine.recommend()의 결과를 그대로 활용, data_generation.py 참조).
"""
import argparse
import os

import pandas as pd

from .data_generation import build_dataset
from .rule_based_filter import apply_no_propulsion_rule, split_for_pipeline
from .preprocessing import encode_rf_class, make_splits, fit_scaler, transform_features, LABEL_COLUMN
from .model import train_with_cv
from .evaluate import evaluate_split, check_overfit_gap, plot_confusion_matrix, plot_learning_curve
from .predict import save_bundle


def main(n_scenarios: int = 40, seed: int = 42, output_dir: str = "outputs/threat_ml"):
    os.makedirs(output_dir, exist_ok=True)

    print(f"[INFO] cuas 시뮬레이터로 시나리오 {n_scenarios}개 생성 -> RADAR/RF 특징 추출")
    df = build_dataset(n_scenarios=n_scenarios, base_seed=seed)
    df = encode_rf_class(df)
    print(f"\n전체 관측 수: {len(df)} (트랙 수: {df['group_id'].nunique()})")
    print(df[LABEL_COLUMN].value_counts())

    df = apply_no_propulsion_rule(df)
    pre_filtered_df, needs_ml_df = split_for_pipeline(df)
    print("\n[1단계: 규칙 기반 사전분류]")
    print(f" - 규칙으로 LOW 확정: {len(pre_filtered_df)}건 ({len(pre_filtered_df) / len(df) * 100:.1f}%)")
    print(f" - ML 정밀분류 필요(추진/RF 신호 존재): {len(needs_ml_df)}건")
    if len(pre_filtered_df):
        correct = (pre_filtered_df[LABEL_COLUMN] == "LOW").mean()
        print(f" - 규칙 기반 LOW 판정의 실제 LOW 일치율: {correct * 100:.1f}%")

    train_df, val_df, test_df = make_splits(needs_ml_df, test_size=0.2, val_size=0.2, seed=seed)
    print("\n[2단계: ML 정밀분류 데이터 분할 (트랙 단위, leakage 방지)]")
    print(f" - Train: {len(train_df)}  Val: {len(val_df)}  Test: {len(test_df)}")

    scaler = fit_scaler(train_df)
    X_train = transform_features(train_df, scaler)
    X_val = transform_features(val_df, scaler)
    X_test = transform_features(test_df, scaler)
    y_train, y_val, y_test = train_df[LABEL_COLUMN], val_df[LABEL_COLUMN], test_df[LABEL_COLUMN]

    trained = train_with_cv(X_train, y_train, seed=seed)
    print("\n[모델 선택 결과]")
    print(f" - 채택 모델: {trained.model_name}")
    print(f" - 최적 하이퍼파라미터: {trained.best_params}")
    print(f" - 교차검증 F1(macro): {trained.cv_best_score:.4f}")

    train_acc = evaluate_split(trained.estimator, X_train, y_train, "Train")
    val_acc = evaluate_split(trained.estimator, X_val, y_val, "Validation")
    evaluate_split(trained.estimator, X_test, y_test, "Test (최종 1회 평가)")
    check_overfit_gap(train_acc, val_acc)

    labels = sorted(y_train.unique())
    plot_confusion_matrix(trained.estimator, X_test, y_test, labels,
                           out_path=os.path.join(output_dir, "confusion_matrix_test.png"))
    plot_learning_curve(trained.estimator, X_train, y_train,
                         out_path=os.path.join(output_dir, "learning_curve.png"), seed=seed)

    needs_ml_df = needs_ml_df.copy()
    needs_ml_df["stage2_predicted_threat"] = trained.estimator.predict(
        transform_features(needs_ml_df, scaler))
    pre_filtered_df = pre_filtered_df.copy()
    pre_filtered_df["stage2_predicted_threat"] = "LOW"

    final_df = pd.concat([pre_filtered_df, needs_ml_df], axis=0)
    final_path = os.path.join(output_dir, "final_classification_result.csv")
    final_df.to_csv(final_path, index=False)
    print(f"\n[최종 결과] 저장 -> {final_path}")
    print(final_df["stage2_predicted_threat"].value_counts())

    bundle_path = os.path.join(output_dir, "model_bundle.joblib")
    save_bundle(scaler, trained.estimator, bundle_path)
    print(f"모델 번들 저장 -> {bundle_path} (predict.load_bundle()로 재사용)")

    return trained, final_df


def _cli():
    ap = argparse.ArgumentParser(description="cuas RADAR/RF 기반 threat_level 사전분류기 학습")
    ap.add_argument("--scenarios", type=int, default=40, help="생성할 시나리오 수")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="outputs/threat_ml")
    args = ap.parse_args()
    main(n_scenarios=args.scenarios, seed=args.seed, output_dir=args.out)


if __name__ == "__main__":
    _cli()
