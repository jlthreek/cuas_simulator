"""
evaluate.py
-----------
모델 성능 평가 + 과적합 여부 진단 (원본 sensor_threat_classifier와 동일 로직).

1. Train 정확도 vs Val/Test 정확도 격차 확인 (격차가 크면 과적합 의심)
2. Learning Curve: 샘플 수 증가에 따른 train/val 점수 수렴 여부 확인
3. Classification report(정밀도/재현율/F1) + Confusion Matrix
"""
from typing import Any
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import learning_curve, StratifiedKFold


def evaluate_split(model: Any, X, y, split_name: str) -> float:
    preds = model.predict(X)
    acc = accuracy_score(y, preds)
    print(f"\n=== [{split_name}] 성능 ===")
    print(f"Accuracy: {acc:.4f}")
    print(classification_report(y, preds, zero_division=0))
    return acc


def check_overfit_gap(train_acc: float, val_acc: float, threshold: float = 0.08):
    gap = train_acc - val_acc
    print(f"\nTrain-Val 정확도 격차: {gap:.4f} (임계값 {threshold})")
    if gap > threshold:
        print("과적합 의심: Train 성능이 Val 대비 크게 높음. "
              "정규화 강화 또는 모델 단순화를 검토하세요.")
    else:
        print("Train-Val 격차 양호: 과적합 징후 뚜렷하지 않음.")
    return gap


def plot_confusion_matrix(model: Any, X, y, labels, out_path: str):
    preds = model.predict(X)
    cm = confusion_matrix(y, preds, labels=labels)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    fig, ax = plt.subplots(figsize=(5, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Confusion Matrix (Test Set)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Confusion matrix 저장: {out_path}")


def plot_learning_curve(estimator: Any, X, y, out_path: str, seed: int = 42):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    train_sizes, train_scores, val_scores = learning_curve(
        estimator, X, y, cv=cv, scoring="f1_macro",
        train_sizes=np.linspace(0.2, 1.0, 5), n_jobs=-1,
    )
    train_mean = train_scores.mean(axis=1)
    val_mean = val_scores.mean(axis=1)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(train_sizes, train_mean, "o-", label="Train F1(macro)")
    ax.plot(train_sizes, val_mean, "o-", label="Validation F1(macro)")
    ax.set_xlabel("Training samples")
    ax.set_ylabel("F1 (macro)")
    ax.set_title("Learning Curve (Overfitting Diagnosis)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Learning curve 저장: {out_path}")
