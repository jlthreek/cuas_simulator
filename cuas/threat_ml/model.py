"""
model.py
--------
2단계 정밀분류 모델: 추진/RF 신호가 있는 표적을 MEDIUM/HIGH(및 소수 노이즈성 LOW)로
분류한다. (LOW는 이미 rule_based_filter.py에서 규칙으로 확정된다.)

과적합 방지 전략(원본 sensor_threat_classifier와 동일):
1. 모델 자체를 단순/정규화된 형태로 제한
   - LogisticRegression: L2 정규화(C 그리드서치로 최적 강도 탐색)
   - RandomForest: max_depth, min_samples_leaf로 트리 복잡도 제한
2. GridSearchCV + StratifiedKFold(교차검증)로 하이퍼파라미터를 검증 성능 기준 선택
   (테스트셋은 하이퍼파라미터 튜닝에 사용하지 않음)
3. 두 모델(로지스틱회귀 vs 랜덤포레스트) 비교 후 검증 성능이 좋은 쪽 채택
"""
from dataclasses import dataclass
from typing import Dict, Any

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold


@dataclass
class TrainedModel:
    estimator: Any
    best_params: Dict[str, Any]
    cv_best_score: float
    model_name: str


def train_with_cv(X_train, y_train, seed: int = 42) -> TrainedModel:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)

    candidates = []

    logreg_grid = GridSearchCV(
        estimator=LogisticRegression(max_iter=2000),
        param_grid={"C": [0.01, 0.1, 1.0, 10.0]},
        scoring="f1_macro",
        cv=cv,
        n_jobs=-1,
    )
    logreg_grid.fit(X_train, y_train)
    candidates.append(TrainedModel(
        estimator=logreg_grid.best_estimator_,
        best_params=logreg_grid.best_params_,
        cv_best_score=logreg_grid.best_score_,
        model_name="LogisticRegression(L2)",
    ))

    rf_grid = GridSearchCV(
        estimator=RandomForestClassifier(random_state=seed),
        param_grid={
            "n_estimators": [100, 200],
            "max_depth": [3, 4, 5],
            "min_samples_leaf": [5, 10],
            "max_features": ["sqrt"],
        },
        scoring="f1_macro",
        cv=cv,
        n_jobs=-1,
    )
    rf_grid.fit(X_train, y_train)
    candidates.append(TrainedModel(
        estimator=rf_grid.best_estimator_,
        best_params=rf_grid.best_params_,
        cv_best_score=rf_grid.best_score_,
        model_name="RandomForest(depth-limited)",
    ))

    best = max(candidates, key=lambda c: c.cv_best_score)
    return best
