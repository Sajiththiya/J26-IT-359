"""Calculate and validate transparent Habitat Risk Index scenarios.

This is index construction, not machine-learning model training. The complete
code is mirrored as numbered cells in
notebooks/hri/06_habitat_risk_index_construction.ipynb.
"""

# %% 1. Imports, paths and frozen analysis choices
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.stats import rankdata, spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/processed/hri/pre_hri_v1"
MASTER_PATH = SOURCE_DIR / "master_cell_year_dataset.csv"
GRID_PATH = ROOT / "data/interim/spatial/lka_laea_5000m_grid.geojson"
BIRD_PATH = ROOT / "data/processed/hri/wp2_v1/hri_cell_year_species_evidence.csv"
OUT = ROOT / "data/processed/hri/hri_v1"
FIGURES = OUT / "figures"
KEY = ["cell_id", "reference_year"]
YEARS = list(range(2010, 2024))
REFERENCE_YEARS = list(range(2010, 2015))
CLIMATE_SCALE_YEARS = list(range(2015, 2020))
MIN_BASELINE_FOREST_LAND_FRACTION = 0.10
RANDOM_SEED = 42

RAW = {
    "forest_amount": "forest__remaining_baseline_forest_proportion",
    "recent_loss": "forest__previous_3yr_loss_fraction_of_baseline",
    "cumulative_loss": "forest__cumulative_prior_loss_fraction_of_baseline",
    "fragmentation": "fragmentation__edge_m_per_land_ha",
    "temperature": "climate__temperature_c_anomaly",
    "precipitation": "climate__precipitation_mm_anomaly",
    "population": "pressure__population_density_per_km2",
}
CORE_RISKS = ["forest_amount_risk", "recent_loss_risk",
              "cumulative_loss_risk", "fragmentation_risk"]

WEIGHTS = {
    # Primary: transparent equal contribution; not claimed expert weights.
    "core_equal": json.loads((ROOT / "configs/hri.json").read_text())["weights"],
    # Analytical alternatives used only for sensitivity.
    "core_condition_emphasis": dict(zip(CORE_RISKS, [0.40, 0.20, 0.20, 0.20])),
    "core_disturbance_emphasis": dict(zip(CORE_RISKS, [0.15, 0.35, 0.30, 0.20])),
    "climate_enhanced_exploratory": {
        **dict(zip(CORE_RISKS, [0.20] * 4)),
        "temperature_stress_risk": 0.10,
        "precipitation_stress_risk": 0.10,
    },
    "pressure_enhanced": {
        **dict(zip(CORE_RISKS, [0.20] * 4)),
        "population_pressure_risk": 0.20,
    },
}

if set(WEIGHTS["core_equal"]) != set(CORE_RISKS) or not np.isclose(sum(WEIGHTS["core_equal"].values()), 1):
    raise ValueError("Configured HRI core weights must cover all four indicators and sum to one")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str) + "\n")


# %% 2. Load and validate the cell-year evidence
def load_master():
    data = pd.read_csv(MASTER_PATH, low_memory=False)
    assert len(data) == 40166
    assert not data.duplicated(KEY).any()
    assert sorted(data.reference_year.unique()) == YEARS
    assert data.cell_id.nunique() == 2869
    assert data[RAW.values()].replace([np.inf, -np.inf], np.nan).notna().sum().ge(0).all()
    data = data.sort_values(KEY).reset_index(drop=True)
    data["mapped_land_ha"] = data["fragmentation__mapped_land_pixels"] * 30 * 30 / 10000
    data["baseline_forest_land_fraction"] = (
        data["forest__baseline_forest_ha"] / data.mapped_land_ha.replace(0, np.nan)
    ).clip(0, 1)
    return data


# %% 3. Define applicability, fixed transformations and component risks
def log_cap_scale(values, upper):
    """Map a non-negative pressure to 0–1 using a frozen reference P99."""
    result = np.log1p(values.clip(lower=0)) / np.log1p(upper)
    return result.clip(0, 1).where(values.notna())


def prepare_components(data):
    d = data.copy()
    core_raw_available = d[[RAW[x] for x in ["forest_amount", "recent_loss",
                                              "cumulative_loss", "fragmentation"]]].notna().all(axis=1)
    coverage_pass = (d["forest__feature_status"].eq("coverage_pass") &
                     d["fragmentation__fragmentation_status"].isin(["coverage_pass", "no_forest"]))
    relevant_baseline = d.baseline_forest_land_fraction.ge(MIN_BASELINE_FOREST_LAND_FRACTION)
    d["core_hri_eligible"] = core_raw_available & coverage_pass & relevant_baseline
    d["core_hri_ineligibility_reason"] = np.select(
        [~core_raw_available, ~coverage_pass, ~relevant_baseline],
        ["missing_core_measurement", "insufficient_source_coverage",
         "baseline_forest_below_10pct_of_cell_land"], default="eligible")

    reference = d.loc[d.reference_year.isin(REFERENCE_YEARS) & d.core_hri_eligible]
    scale_parameters = {
        "recent_loss_p99_2010_2014": float(reference[RAW["recent_loss"]].quantile(.99)),
        "cumulative_loss_p99_2010_2014": float(reference[RAW["cumulative_loss"]].quantile(.99)),
        "edge_density_p99_2010_2014": float(reference[RAW["fragmentation"]].quantile(.99)),
    }
    assert all(np.isfinite(x) and x > 0 for x in scale_parameters.values())

    # Forest amount is current surviving baseline forest divided by mapped land.
    # The >=10% baseline applicability rule prevents naturally near-zero forest
    # cells from entering the primary forest-oriented index without review.
    d["forest_amount_risk"] = (1 - d[RAW["forest_amount"]].clip(0, 1)).where(d.core_hri_eligible)
    d["recent_loss_risk"] = log_cap_scale(
        d[RAW["recent_loss"]], scale_parameters["recent_loss_p99_2010_2014"]).where(d.core_hri_eligible)
    d["cumulative_loss_risk"] = log_cap_scale(
        d[RAW["cumulative_loss"]], scale_parameters["cumulative_loss_p99_2010_2014"]).where(d.core_hri_eligible)
    d["fragmentation_risk"] = log_cap_scale(
        d[RAW["fragmentation"]], scale_parameters["edge_density_p99_2010_2014"]).where(d.core_hri_eligible)
    # A forest-free cell has no edges, but zero edge density must not mean low risk.
    no_forest = d.core_hri_eligible & d["fragmentation__no_forest"]
    d.loc[no_forest, "fragmentation_risk"] = 1.0

    climate_reference = d.loc[d.reference_year.isin(CLIMATE_SCALE_YEARS) & d.core_hri_eligible]
    scale_parameters.update({
        "absolute_temperature_anomaly_p99_2015_2019": float(climate_reference[RAW["temperature"]].abs().quantile(.99)),
        "absolute_precipitation_anomaly_p99_2015_2019": float(climate_reference[RAW["precipitation"]].abs().quantile(.99)),
        "log_population_density_p99_2010_2014": float(np.log1p(reference[RAW["population"]]).quantile(.99)),
    })
    d["temperature_stress_risk"] = log_cap_scale(
        d[RAW["temperature"]].abs(), scale_parameters["absolute_temperature_anomaly_p99_2015_2019"])
    d["precipitation_stress_risk"] = log_cap_scale(
        d[RAW["precipitation"]].abs(), scale_parameters["absolute_precipitation_anomaly_p99_2015_2019"])
    population_upper = np.expm1(scale_parameters["log_population_density_p99_2010_2014"])
    d["population_pressure_risk"] = log_cap_scale(d[RAW["population"]], population_upper)

    for column in [*CORE_RISKS, "temperature_stress_risk", "precipitation_stress_risk",
                   "population_pressure_risk"]:
        assert d[column].dropna().between(0, 1).all(), column
    return d, scale_parameters


# %% 4. Calculate five explicit HRI scenarios and risk classes
def weighted_score(data, weights):
    assert np.isclose(sum(weights.values()), 1)
    fields = list(weights)
    eligible = data[fields].notna().all(axis=1) & data.core_hri_eligible
    score = sum(data[field] * weight for field, weight in weights.items()) * 100
    return score.where(eligible), eligible


def fixed_class(score):
    return pd.cut(score, [-np.inf, 100 / 3, 200 / 3, np.inf],
                  labels=["Low", "Moderate", "High"], right=True).astype("string")


def calculate_scenarios(data):
    rows, thresholds = [], []
    for version, weights in WEIGHTS.items():
        score, eligible = weighted_score(data, weights)
        q33, q67 = score.dropna().quantile([1 / 3, 2 / 3])
        quantile_class = pd.cut(score, [-np.inf, q33, q67, np.inf],
                                labels=["Low", "Moderate", "High"], include_lowest=True).astype("string")
        status = np.where(eligible, "eligible", "ineligible_or_missing_scenario_component")
        part = data[KEY + ["core_hri_ineligibility_reason"]].copy()
        part["hri_version"] = version
        part["hri_score_0_100"] = score
        part["fixed_risk_class"] = fixed_class(score)
        part["quantile_risk_class"] = quantile_class
        part["hri_status"] = status
        for field in [*CORE_RISKS, "temperature_stress_risk", "precipitation_stress_risk",
                      "population_pressure_risk"]:
            part[field] = data[field]
            part[field + "_weight"] = weights.get(field, 0.0)
        rows.append(part)
        thresholds.append({"hri_version": version, "method": "fixed", "low_upper": 100 / 3,
                           "moderate_upper": 200 / 3, "reference_rows": int(score.notna().sum())})
        thresholds.append({"hri_version": version, "method": "pooled_quantile_terciles",
                           "low_upper": q33, "moderate_upper": q67,
                           "reference_rows": int(score.notna().sum())})
    result = pd.concat(rows, ignore_index=True)
    assert not result.duplicated(KEY + ["hri_version"]).any()
    return result, pd.DataFrame(thresholds)


# %% 5. Sensitivity to weights, indicators, eligibility and canopy threshold
def rank_comparison(primary, alternative, label, analysis_type):
    paired = pd.concat([primary.rename("primary"), alternative.rename("alternative")], axis=1).dropna()
    n_top = max(1, int(np.ceil(len(paired) * .10)))
    top_primary = set(paired.nlargest(n_top, "primary").index)
    top_alternative = set(paired.nlargest(n_top, "alternative").index)
    return {"analysis_type": analysis_type, "scenario": label, "paired_rows": len(paired),
            "spearman_r": paired.corr(method="spearman").iloc[0, 1],
            "mean_absolute_score_change": (paired.primary - paired.alternative).abs().mean(),
            "top10pct_jaccard": len(top_primary & top_alternative) / len(top_primary | top_alternative)}


def run_sensitivity(data, scores):
    primary = scores.query("hri_version == 'core_equal'").set_index(KEY).hri_score_0_100
    indexed = data.set_index(KEY)
    results = []
    for version in ["core_condition_emphasis", "core_disturbance_emphasis"]:
        alternative = scores.query("hri_version == @version").set_index(KEY).hri_score_0_100
        results.append(rank_comparison(primary, alternative, version, "predefined_weight_scenario"))
    for version in ["climate_enhanced_exploratory", "pressure_enhanced"]:
        alternative = scores.query("hri_version == @version").set_index(KEY).hri_score_0_100
        results.append(rank_comparison(primary, alternative, version, "extension_vs_core_on_available_rows"))

    rng = np.random.default_rng(RANDOM_SEED)
    matrix = indexed[CORE_RISKS].to_numpy()
    valid = indexed.core_hri_eligible.to_numpy() & np.isfinite(matrix).all(axis=1)
    reference_values = primary.to_numpy()[valid]
    reference_index = indexed.index[valid]
    n_top = max(1, int(np.ceil(valid.sum() * .10)))
    top_reference = set(reference_index[np.argpartition(reference_values, -n_top)[-n_top:]])
    for i, weights in enumerate(rng.dirichlet(np.repeat(20.0, 4), size=200), 1):
        alternative_values = matrix[valid] @ weights * 100
        top = set(reference_index[np.argpartition(alternative_values, -n_top)[-n_top:]])
        results.append({"analysis_type": "dirichlet_weight_perturbation", "scenario": f"draw_{i:03d}",
                        "paired_rows": int(valid.sum()),
                        "spearman_r": spearmanr(reference_values, alternative_values).statistic,
                        "mean_absolute_score_change": np.abs(reference_values - alternative_values).mean(),
                        "top10pct_jaccard": len(top_reference & top) / len(top_reference | top),
                        **{f"weight_{field}": weight for field, weight in zip(CORE_RISKS, weights)}})

    for omitted in CORE_RISKS:
        remaining = [x for x in CORE_RISKS if x != omitted]
        alternative = indexed[remaining].mean(axis=1, skipna=False) * 100
        alternative = alternative.where(indexed.core_hri_eligible)
        results.append(rank_comparison(primary, alternative, f"omit_{omitted}", "leave_one_indicator_out"))

    for threshold in [0.05, 0.10, 0.20]:
        alternative = indexed[CORE_RISKS].mean(axis=1, skipna=False) * 100
        eligible = (indexed.core_hri_eligible | indexed.core_hri_ineligibility_reason.eq(
            "baseline_forest_below_10pct_of_cell_land")) & indexed.baseline_forest_land_fraction.ge(threshold)
        alternative = alternative.where(eligible)
        results.append(rank_comparison(primary, alternative, f"baseline_forest_land_fraction_gte_{threshold}",
                                       "applicability_threshold"))

    # Existing all-country forest sensitivity and sampled fragmentation sensitivity
    # are reported separately because national 10%/50% fragmentation was not derived.
    forest_rank = pd.read_csv(SOURCE_DIR / "forest_threshold_rank_sensitivity.csv", index_col=0)
    for a, b in [(10, 30), (30, 50), (10, 50)]:
        results.append({"analysis_type": "canopy_threshold_forest_component_only",
                        "scenario": f"{a}_vs_{b}_percent", "paired_rows": np.nan,
                        "spearman_r": forest_rank.loc[a, str(b)] if str(b) in forest_rank else forest_rank.loc[a, b],
                        "mean_absolute_score_change": np.nan, "top10pct_jaccard": np.nan})
    return pd.DataFrame(results)


# %% 6. Validate year-t HRI against observed tree-cover loss in year t+1
def binary_auc(target, score):
    target = np.asarray(target, dtype=bool)
    score = np.asarray(score, dtype=float)
    n1, n0 = target.sum(), (~target).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = rankdata(score)
    return (ranks[target].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def validation_row(frame, version, period):
    f = frame.dropna(subset=["hri_score_0_100", "next_year_loss_fraction"]).copy()
    if not len(f):
        return None
    positive = f.next_year_loss_fraction.gt(0)
    top_cut = f.hri_score_0_100.quantile(.90)
    total_loss = f.next_year_loss_fraction.sum()
    class_means = f.groupby("quantile_risk_class", observed=True).next_year_loss_fraction.mean()
    return {"hri_version": version, "period": period, "rows": len(f),
            "positive_next_year_loss_rows": int(positive.sum()),
            "spearman_hri_vs_next_loss": f[["hri_score_0_100", "next_year_loss_fraction"]].corr(
                method="spearman").iloc[0, 1],
            "auc_any_next_year_loss": binary_auc(positive, f.hri_score_0_100),
            "mean_next_loss_low": class_means.get("Low", np.nan),
            "mean_next_loss_moderate": class_means.get("Moderate", np.nan),
            "mean_next_loss_high": class_means.get("High", np.nan),
            "top10pct_share_of_next_loss": (f.loc[f.hri_score_0_100.ge(top_cut),
                                                   "next_year_loss_fraction"].sum() / total_loss
                                              if total_loss > 0 else np.nan)}


def validate_hri(data, scores):
    targets = data[KEY + ["forest__annual_loss_fraction_of_baseline"]].copy().sort_values(KEY)
    targets["next_year_loss_fraction"] = targets.groupby("cell_id")[
        "forest__annual_loss_fraction_of_baseline"].shift(-1)
    targets["target_year"] = targets.reference_year + 1
    targets.loc[targets.reference_year.eq(max(YEARS)), ["next_year_loss_fraction", "target_year"]] = np.nan
    rows = []
    details = scores.merge(targets[KEY + ["next_year_loss_fraction", "target_year"]],
                           on=KEY, how="left", validate="many_to_one")
    for version, group in details.groupby("hri_version"):
        row = validation_row(group, version, "all_available_years")
        if row:
            rows.append(row)
        for year, annual in group.groupby("reference_year"):
            row = validation_row(annual, version, f"predict_{year + 1}_from_{year}")
            if row:
                rows.append(row)
    # Compare each extension with the core on exactly the extension's rows.
    # Otherwise different climate/population coverage can look like improvement.
    core = details.query("hri_version == 'core_equal'").set_index(KEY)
    for extension, label in [("climate_enhanced_exploratory", "core_equal_climate_matched"),
                             ("pressure_enhanced", "core_equal_pressure_matched")]:
        available_keys = details.query("hri_version == @extension and hri_score_0_100.notna()").set_index(KEY).index
        matched = core.loc[core.index.intersection(available_keys)].reset_index()
        row = validation_row(matched, label, "all_available_years")
        if row:
            rows.append(row)
    return pd.DataFrame(rows), details[KEY + ["hri_version", "hri_score_0_100",
                                             "next_year_loss_fraction", "target_year"]]


# %% 7. Link bird evidence for interpretation without multiplying HRI rows
def build_bird_context(scores):
    birds = pd.read_csv(BIRD_PATH)
    summary = birds.groupby(KEY).agg(
        observed_endemic_species_richness=("accepted_scientific_name", "nunique"),
        bird_observation_records=("observation_record_count", "sum"),
        bird_observation_unique_days=("unique_days", "sum"),
        possible_duplicate_bird_records=("possible_duplicate_records", "sum")).reset_index()
    primary = scores.query("hri_version == 'core_equal'")[
        KEY + ["hri_score_0_100", "fixed_risk_class", "quantile_risk_class"]].copy()
    result = primary.merge(summary, on=KEY, how="left", validate="one_to_one")
    result["bird_evidence_available"] = result.observed_endemic_species_richness.notna()
    # Leave unvisited/unrecorded cell-years missing: no record is not absence.
    return result


# %% 8. Create diagnostic plots and maps
def make_figures(data, scores, validation):
    FIGURES.mkdir(parents=True, exist_ok=True)
    primary = scores.query("hri_version == 'core_equal'")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(primary.hri_score_0_100.dropna(), bins=50, color="#31688e")
    ax.set(xlabel="Core HRI (0–100)", ylabel="Cell-years", title="Core HRI distribution")
    fig.tight_layout(); fig.savefig(FIGURES / "core_hri_distribution.png", dpi=160); plt.close(fig)

    annual = primary.groupby("reference_year").hri_score_0_100.agg(["median", "mean"])
    fig, ax = plt.subplots(figsize=(8, 4)); annual.plot(ax=ax, marker="o")
    ax.set(xlabel="Reference year", ylabel="Core HRI", title="Annual HRI summary")
    fig.tight_layout(); fig.savefig(FIGURES / "core_hri_annual_summary.png", dpi=160); plt.close(fig)

    overall = validation.query("period == 'all_available_years'")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(overall.hri_version, overall.spearman_hri_vs_next_loss)
    ax.tick_params(axis="x", rotation=30); ax.set(ylabel="Spearman r", title="HRI vs next-year tree-cover loss")
    fig.tight_layout(); fig.savefig(FIGURES / "future_loss_validation.png", dpi=160); plt.close(fig)

    grid = gpd.read_file(GRID_PATH).to_crs("EPSG:4326")
    latest = primary.query("reference_year == 2023")[["cell_id", "hri_score_0_100"]]
    mapped = grid.merge(latest, on="cell_id", how="left", validate="one_to_one")
    fig, ax = plt.subplots(figsize=(7, 9)); mapped.plot(column="hri_score_0_100", cmap="magma_r",
        legend=True, missing_kwds={"color": "lightgrey", "label": "Not eligible"}, ax=ax)
    ax.set_axis_off(); ax.set_title("Core environmental HRI, 2023")
    fig.tight_layout(); fig.savefig(FIGURES / "core_hri_2023_map.png", dpi=180); plt.close(fig)

    wide = primary.pivot(index="cell_id", columns="reference_year", values="hri_score_0_100")
    change = (wide[2023] - wide[2010]).rename("hri_change_2010_2023").reset_index()
    mapped = grid.merge(change, on="cell_id", how="left", validate="one_to_one")
    fig, ax = plt.subplots(figsize=(7, 9)); mapped.plot(column="hri_change_2010_2023", cmap="coolwarm",
        legend=True, missing_kwds={"color": "lightgrey"}, ax=ax)
    ax.set_axis_off(); ax.set_title("Change in core HRI, 2010–2023")
    fig.tight_layout(); fig.savefig(FIGURES / "core_hri_change_2010_2023_map.png", dpi=180); plt.close(fig)


# %% 9. Save definitions, scores, sensitivity, validation and audit
def indicator_definitions(scale_parameters):
    return pd.DataFrame([
        {"indicator": "forest_amount_risk", "source_column": RAW["forest_amount"],
         "direction": "lower remaining forest share -> higher risk", "transformation": "1 - clipped raw proportion",
         "temporal_window": "surviving year-2000 baseline tree cover at end of t", "role": "core"},
        {"indicator": "recent_loss_risk", "source_column": RAW["recent_loss"],
         "direction": "higher prior three-year loss -> higher risk",
         "transformation": "log1p(x) / log1p(P99 in 2010-2014), clipped 0-1",
         "temporal_window": "t-3 through t-1", "role": "core"},
        {"indicator": "cumulative_loss_risk", "source_column": RAW["cumulative_loss"],
         "direction": "higher cumulative prior loss -> higher risk",
         "transformation": "log1p(x) / log1p(P99 in 2010-2014), clipped 0-1",
         "temporal_window": "2001 through t-1", "role": "core; omission sensitivity required"},
        {"indicator": "fragmentation_risk", "source_column": RAW["fragmentation"],
         "direction": "higher edge density -> higher risk; forest-free eligible cell forced to 1",
         "transformation": "log1p(x) / log1p(P99 in 2010-2014), clipped 0-1",
         "temporal_window": "forest mask at end of t", "role": "core"},
        {"indicator": "temperature_stress_risk", "source_column": RAW["temperature"],
         "direction": "larger absolute anomaly treated as exploratory stress",
         "transformation": "log1p(abs(x)) / log1p(P99 absolute anomaly in 2015-2019)",
         "temporal_window": "year t relative to 2010-2014 reference", "role": "exploratory climate scenario"},
        {"indicator": "precipitation_stress_risk", "source_column": RAW["precipitation"],
         "direction": "larger absolute anomaly treated as exploratory stress",
         "transformation": "log1p(abs(x)) / log1p(P99 absolute anomaly in 2015-2019)",
         "temporal_window": "year t relative to 2010-2014 reference", "role": "exploratory climate scenario"},
        {"indicator": "population_pressure_risk", "source_column": RAW["population"],
         "direction": "higher modelled population density -> higher pressure proxy",
         "transformation": "log1p(x) / P99 log1p density in 2010-2014, clipped 0-1",
         "temporal_window": "year t, 2010-2020 only", "role": "pressure scenario"},
    ]).assign(scale_parameters=json.dumps(scale_parameters, sort_keys=True), weight="scenario-specific")


def run():
    OUT.mkdir(parents=True, exist_ok=True); FIGURES.mkdir(exist_ok=True)
    data = load_master()
    data, scales = prepare_components(data)
    scores, class_thresholds = calculate_scenarios(data)
    sensitivity = run_sensitivity(data, scores)
    validation, validation_detail = validate_hri(data, scores)
    birds = build_bird_context(scores)
    make_figures(data, scores, validation)

    scores.to_csv(OUT / "hri_cell_year_scores.csv", index=False)
    # Convenience releases contain only the fields used by each scenario and
    # only rows with a defensible score. They avoid irrelevant blank extension
    # columns without inventing measurements or altering the audited full table.
    scenario_components = {
        "core_equal": CORE_RISKS,
        "climate_enhanced_exploratory": [*CORE_RISKS, "temperature_stress_risk",
                                          "precipitation_stress_risk"],
        "pressure_enhanced": [*CORE_RISKS, "population_pressure_risk"],
    }
    for version, components in scenario_components.items():
        keep = KEY + ["hri_version", *components, "hri_score_0_100",
                      "fixed_risk_class", "quantile_risk_class", "hri_status"]
        complete = scores.loc[scores.hri_version.eq(version) & scores.hri_score_0_100.notna(), keep]
        assert complete[components + ["hri_score_0_100", "fixed_risk_class",
                                      "quantile_risk_class"]].notna().all().all()
        complete.to_csv(OUT / f"hri_{version}_complete_cases.csv", index=False)
    indicator_definitions(scales).to_csv(OUT / "hri_indicator_definitions.csv", index=False)
    pd.DataFrame([{"hri_version": version, "indicator": indicator, "weight": weight,
                   "weight_status": "transparent analytical scenario; not expert-elicited"}
                  for version, weights in WEIGHTS.items() for indicator, weight in weights.items()]).to_csv(
                      OUT / "hri_weight_scenarios.csv", index=False)
    class_thresholds.to_csv(OUT / "hri_class_thresholds.csv", index=False)
    sensitivity.to_csv(OUT / "hri_sensitivity_results.csv", index=False)
    validation.to_csv(OUT / "hri_validation_results.csv", index=False)
    validation_detail.to_csv(OUT / "hri_validation_cell_year.csv", index=False)
    birds.to_csv(OUT / "hri_bird_context.csv", index=False)

    missing = scores.groupby("hri_version").agg(
        total_rows=("cell_id", "size"), scored_rows=("hri_score_0_100", "count"))
    missing["missing_or_ineligible_rows"] = missing.total_rows - missing.scored_rows
    missing["scored_fraction"] = missing.scored_rows / missing.total_rows
    missing.to_csv(OUT / "hri_missing_data_report.csv")
    scores.groupby(["hri_version", "hri_status", "core_hri_ineligibility_reason"],
                   dropna=False).size().rename("rows").reset_index().to_csv(
                       OUT / "hri_ineligibility_reasons.csv", index=False)

    primary = scores.query("hri_version == 'core_equal'")
    audit = {
        "method_version": "hri-v1-transparent-scenarios",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_unit": "one cell_id x reference_year x hri_version",
        "rows": len(scores), "duplicate_primary_keys": int(scores.duplicated(KEY + ["hri_version"]).sum()),
        "primary_hri_version": "core_equal", "primary_scored_rows": int(primary.hri_score_0_100.notna().sum()),
        "primary_score_min": float(primary.hri_score_0_100.min()),
        "primary_score_max": float(primary.hri_score_0_100.max()),
        "primary_score_out_of_range": int((~primary.hri_score_0_100.dropna().between(0, 100)).sum()),
        "baseline_forest_applicability_threshold": MIN_BASELINE_FOREST_LAND_FRACTION,
        "working_canopy_threshold_percent": 30,
        "scale_parameters": scales,
        "future_information_check": "core loss windows end at t-1; fragmentation/forest amount end at t; validation target is t+1",
        "climate_warning": "absolute anomalies are an exploratory sensitivity assumption, not species-specific tolerance",
        "population_warning": "pressure scenario ends in 2020; weights are not renormalized after source coverage ends",
        "ecological_scope": "forest-oriented relative environmental risk; not habitat suitability or species absence",
        "bird_interpretation": "bird evidence is separate; no record is not absence",
        "weights_status": "equal primary and analytical alternatives; literature/expert weights not obtained",
        "canopy_sensitivity_limit": "forest components national; 10/50% fragmentation sensitivity sampled, not national HRI",
        "five_km_scale_status": "provisional; an alternative assessment grid was not computed",
        "model_training_performed": False,
        "input_sha256": {str(path.relative_to(ROOT)): sha256(path)
                         for path in [MASTER_PATH, GRID_PATH, BIRD_PATH, ROOT / "scripts/calculate_hri.py"]},
        "outputs": sorted(str(x.relative_to(OUT)) for x in OUT.glob("*.csv")),
    }
    assert audit["duplicate_primary_keys"] == 0 and audit["primary_score_out_of_range"] == 0
    write_json(OUT / "hri_audit.json", audit)
    print(json.dumps({k: audit[k] for k in ["rows", "duplicate_primary_keys", "primary_scored_rows",
                                             "primary_score_min", "primary_score_max"]}, indent=2))
    print("Saved HRI release:", OUT)


# %% 10. Foreground execution
if __name__ == "__main__":
    run()
