"""Grouped cross-validation experiments for the frozen HRI model_v1 splits.

Run from a notebook in this directory or as ``python optimized_training.py --model all``.
The holdout test is read only by ``--final-test MODEL`` after model selection.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, RandomizedSearchCV
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
from sklearn.svm import SVR

COMPONENT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = COMPONENT_ROOT / "data/splits/hri/model_v1"
OUTPUT_DIR = COMPONENT_ROOT / "artifacts/hri/model_training_optimized"
TARGET = "hri_score_0_100"
FEATURES = [
    "climate__annual_mean_temperature_c",
    "climate__annual_precipitation_mm",
    "climate__temperature_c_anomaly",
    "climate__temperature_c_trailing5_slope_per_year",
    "climate__precipitation_mm_anomaly",
    "climate__precipitation_mm_trailing5_slope_per_year",
    "terrain__mean_elevation_m",
    "terrain__elevation_sd_m",
    "terrain__mean_slope_degrees",
]
MODELS = (
    "linear_regression", "random_forest", "extra_trees", "xgboost",
    "lightgbm", "catboost", "svr", "knn", "gam", "mlp",
)


def load_split(name: str) -> pd.DataFrame:
    if name not in {"train", "validation", "test"}:
        raise ValueError(f"Unknown split: {name}")
    frame = pd.read_csv(DATA_DIR / f"{name}.csv")
    required = set(FEATURES + [TARGET, "cell_id", "dataset_split", "reference_year"])
    missing = required.difference(frame)
    if missing:
        raise ValueError(f"{name} lacks columns: {sorted(missing)}")
    if not frame.dataset_split.eq(name).all():
        raise ValueError(f"{name} has inconsistent dataset_split labels")
    if frame[["cell_id", "reference_year"]].duplicated().any():
        raise ValueError(f"{name} has duplicate cell-year keys")
    for col in FEATURES + [TARGET]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame[FEATURES] = frame[FEATURES].replace([np.inf, -np.inf], np.nan)
    valid = np.isfinite(frame[TARGET].to_numpy(dtype=float))
    if not valid.all():
        print(f"{name}: dropping {(~valid).sum()} rows with invalid target")
        frame = frame.loc[valid].copy()
    if frame.empty:
        raise ValueError(f"{name} has no usable rows")
    return frame


def check_groups(*frames: pd.DataFrame) -> None:
    groups = [set(f.cell_id) for f in frames]
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            if groups[i] & groups[j]:
                raise ValueError("cell_id occurs in more than one split")


def model_spec(name: str):
    """Return a fold-safe pipeline and compact, regularization-aware search space."""
    if name == "linear_regression":
        # Ridge includes a near-unregularized option, so this is the linear baseline.
        reg = Ridge()
        params = {"model__alpha": [0.01, 0.1, 1, 10, 100, 1000]}
    elif name == "random_forest":
        reg = RandomForestRegressor(n_estimators=200, n_jobs=4, random_state=42)
        params = {"model__max_depth": [8, 14, None], "model__min_samples_leaf": [2, 5, 10, 20],
                  "model__max_features": [0.6, 1.0], "model__max_samples": [0.7, 0.9]}
    elif name == "extra_trees":
        reg = ExtraTreesRegressor(n_estimators=200, n_jobs=4, random_state=42)
        params = {"model__max_depth": [10, 18, None], "model__min_samples_leaf": [2, 5, 10, 20],
                  "model__max_features": [0.6, 1.0]}
    elif name == "xgboost":
        from xgboost import XGBRegressor
        reg = XGBRegressor(objective="reg:squarederror", tree_method="hist", n_jobs=4,
                           random_state=42)
        params = {"model__n_estimators": [200, 400, 700], "model__max_depth": [2, 4, 6],
                  "model__learning_rate": [0.02, 0.05, 0.1], "model__subsample": [0.7, 0.9],
                  "model__colsample_bytree": [0.7, 1.0], "model__reg_lambda": [1, 5, 20]}
    elif name == "lightgbm":
        from lightgbm import LGBMRegressor
        reg = LGBMRegressor(verbosity=-1, n_jobs=4, random_state=42)
        params = {"model__n_estimators": [200, 400, 700], "model__num_leaves": [7, 15, 31],
                  "model__learning_rate": [0.02, 0.05, 0.1], "model__min_child_samples": [20, 50, 100],
                  "model__colsample_bytree": [0.7, 1.0], "model__reg_lambda": [1, 5, 20]}
    elif name == "catboost":
        from catboost import CatBoostRegressor
        reg = CatBoostRegressor(loss_function="RMSE", verbose=False, allow_writing_files=False,
                                thread_count=4, random_seed=42)
        params = {"model__iterations": [250, 500, 750], "model__depth": [3, 5, 7],
                  "model__learning_rate": [0.02, 0.05, 0.1], "model__l2_leaf_reg": [3, 10, 30]}
    elif name == "svr":
        reg = SVR(kernel="rbf", cache_size=1000)
        params = {"model__C": [0.3, 1, 3, 10, 30], "model__epsilon": [0.3, 1, 2],
                  "model__gamma": ["scale", 0.01, 0.1]}
    elif name == "knn":
        reg = KNeighborsRegressor(n_jobs=4)
        params = {"model__n_neighbors": [10, 25, 50, 100],
                  "model__weights": ["uniform", "distance"], "model__p": [1, 2]}
    elif name == "gam":
        # Additive spline basis with Ridge shrinkage; no feature interactions.
        reg = Ridge()
        params = {"preprocess__splines__n_knots": [4, 6, 8],
                  "model__alpha": [1, 10, 100, 1000]}
    elif name == "mlp":
        reg = MLPRegressor(early_stopping=True, validation_fraction=0.15,
                           n_iter_no_change=15, max_iter=300, random_state=42)
        params = {"model__hidden_layer_sizes": [(32,), (64, 32), (128, 64)],
                  "model__alpha": [0.1, 1, 10], "model__learning_rate_init": [0.0005, 0.001]}
    else:
        raise ValueError(f"Unknown model {name!r}; choose from {MODELS}")

    if name == "gam":
        preprocess = Pipeline([("imputer", SimpleImputer(strategy="median")),
                               ("splines", SplineTransformer(degree=3, include_bias=False))])
    elif name in {"linear_regression", "svr", "knn", "mlp"}:
        preprocess = Pipeline([("imputer", SimpleImputer(strategy="median")),
                               ("scaler", StandardScaler())])
    else:
        preprocess = SimpleImputer(strategy="median")
    return Pipeline([("preprocess", preprocess), ("model", reg)]), params


def metrics(y, prediction) -> dict:
    return {"MAE": float(mean_absolute_error(y, prediction)),
            "RMSE": float(np.sqrt(mean_squared_error(y, prediction))),
            "R2": float(r2_score(y, prediction))}


def run_experiment(name: str, n_iter: int = 8, folds: int = 3,
                   output_dir: Path = OUTPUT_DIR) -> dict:
    """Tune on grouped training CV, then report train and untouched validation scores."""
    if (output_dir / name / "final_test_metrics.csv").exists():
        raise FileExistsError("Final test was already evaluated for this model; preserve that result")
    train, validation = load_split("train"), load_split("validation")
    check_groups(train, validation)
    if train.cell_id.nunique() < folds or folds < 2:
        raise ValueError("folds must be at least 2 and no greater than training cell count")
    estimator, space = model_spec(name)
    cv = GroupKFold(n_splits=folds)
    search = RandomizedSearchCV(
        estimator, space, n_iter=n_iter, scoring={"MAE": "neg_mean_absolute_error",
                                           "RMSE": "neg_root_mean_squared_error", "R2": "r2"},
        refit="MAE", cv=cv, n_jobs=1, random_state=42, return_train_score=True,
        error_score="raise", verbose=1,
    )
    started = time.perf_counter()
    search.fit(train[FEATURES], train[TARGET], groups=train.cell_id)
    elapsed = time.perf_counter() - started
    model = search.best_estimator_
    train_pred = model.predict(train[FEATURES])
    val_pred = model.predict(validation[FEATURES])
    baseline = DummyRegressor(strategy="mean").fit(train[FEATURES], train[TARGET])
    baseline_val_mae = mean_absolute_error(validation[TARGET], baseline.predict(validation[FEATURES]))
    best = search.best_index_
    result = {"model": name, "n_train": len(train), "n_validation": len(validation),
              "folds": folds, "candidates": len(search.cv_results_["params"]),
              "cv_MAE": float(-search.cv_results_["mean_test_MAE"][best]),
              "cv_MAE_std": float(search.cv_results_["std_test_MAE"][best]),
              "cv_RMSE": float(-search.cv_results_["mean_test_RMSE"][best]),
              "cv_R2": float(search.cv_results_["mean_test_R2"][best]),
              "cv_train_MAE": float(-search.cv_results_["mean_train_MAE"][best]),
              "train_MAE": metrics(train[TARGET], train_pred)["MAE"],
              "baseline_validation_MAE": float(baseline_val_mae),
              "validation_MAE": metrics(validation[TARGET], val_pred)["MAE"],
              "validation_RMSE": metrics(validation[TARGET], val_pred)["RMSE"],
              "validation_R2": metrics(validation[TARGET], val_pred)["R2"],
              "train_validation_MAE_gap": float(metrics(validation[TARGET], val_pred)["MAE"]
                                                - metrics(train[TARGET], train_pred)["MAE"]),
              "seconds": elapsed, "best_params": search.best_params_}
    dest = output_dir / name
    dest.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(search.cv_results_).to_csv(dest / "cv_results.csv", index=False)
    pd.DataFrame([result]).drop(columns="best_params").to_csv(dest / "metrics.csv", index=False)
    (dest / "best_params.json").write_text(json.dumps(result["best_params"], indent=2))
    predictions = validation[["cell_id", "reference_year", TARGET]].copy()
    predictions["prediction"] = val_pred
    predictions["residual"] = predictions[TARGET] - predictions.prediction
    predictions.to_csv(dest / "validation_predictions.csv", index=False)
    if "fixed_risk_class" in validation:
        predictions["fixed_risk_class"] = validation.fixed_risk_class.to_numpy()
        (predictions.assign(absolute_error=lambda d: d.residual.abs())
         .groupby("fixed_risk_class", dropna=False)
         .agg(n=(TARGET, "size"), MAE=("absolute_error", "mean"),
              mean_residual=("residual", "mean"))
         .to_csv(dest / "validation_by_risk_class.csv"))
    joblib.dump(model, dest / "model.joblib")
    print(pd.DataFrame([result]).drop(columns="best_params").to_string(index=False))
    print("Best parameters:", result["best_params"])
    return result


def run_all(n_iter: int = 8, folds: int = 3,
            output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:
    rows = [run_experiment(name, n_iter, folds, output_dir) for name in MODELS]
    comparison = pd.DataFrame(rows).drop(columns="best_params").sort_values("validation_MAE")
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_dir / "model_comparison.csv", index=False)
    return comparison


def final_test(name: str, output_dir: Path = OUTPUT_DIR) -> dict:
    """Explicit final holdout evaluation of a previously selected model."""
    if name not in MODELS:
        raise ValueError(f"Unknown model: {name}")
    model_path = output_dir / name / "model.joblib"
    if (output_dir / name / "final_test_metrics.csv").exists():
        raise FileExistsError("Final test was already evaluated for this model")
    if not model_path.exists():
        raise FileNotFoundError(f"Run training first: {model_path}")
    test = load_split("test")
    check_groups(load_split("train"), load_split("validation"), test)
    model = joblib.load(model_path)
    pred = model.predict(test[FEATURES])
    result = {"model": name, "split": "test", "n": len(test), **metrics(test[TARGET], pred)}
    dest = output_dir / name
    pd.DataFrame([result]).to_csv(dest / "final_test_metrics.csv", index=False)
    predictions = test[["cell_id", "reference_year", TARGET]].copy()
    predictions["prediction"] = pred
    predictions.to_csv(dest / "final_test_predictions.csv", index=False)
    print(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--model", choices=(*MODELS, "all"))
    choice.add_argument("--final-test", choices=MODELS, metavar="MODEL")
    parser.add_argument("--n-iter", type=int, default=8)
    parser.add_argument("--folds", type=int, default=3)
    args = parser.parse_args()
    if args.final_test:
        final_test(args.final_test)
    elif args.model == "all":
        print(run_all(args.n_iter, args.folds).to_string(index=False))
    else:
        run_experiment(args.model, args.n_iter, args.folds)


if __name__ == "__main__":
    main()
