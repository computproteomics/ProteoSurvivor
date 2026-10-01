"""
Unit tests for game station simulator functions in services.py.
One test class per station, testing the primary success path and the
integration behavior.
"""

from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management import call_command
from django.test import TestCase
from django.test import TestCase
from django.test.client import RequestFactory
from io import StringIO
import itertools
import json
import numpy as np
import pandas as pd
from pathlib import Path

from game.services import (
    _to_json_safe,
    _simulate_data_review,
    _simulate_filtering,
    _simulate_imputer,
    _simulate_mass_spec,
    _simulate_multiple_testing_corrector,
    _simulate_normalize,
    _simulate_sample_prep,
    _simulate_spectral_search,
    _simulate_statistical_analysis,
    _simulate_the_cutter,
    _simulate_transform,
    _simulate_final_report,
    run_station,
    COND_A,
    COND_B,
    FC,
    ORGANISM,
    PROTEIN,
    PROTEIN_ID,
    PVALUE,
    TOT_PEP,
    _squeeze_var,
)
from game.models import FinalStationResult, StationRun
from game.serializers import DataFrameSessionSerializer

_DUMMY_IMG = "dummy_base64_image"
_ALL_UPSTREAM = {"sample_prep", "mass_spec", "spectral_search"}
_MAX_CONFIG_CASES = 10


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------


def _make_dataset() -> pd.DataFrame:
    """Minimal valid proteomics DataFrame matching the column names used in services.py."""
    data = {
        "Protein": ["P0001", "P0002", "P0003", "P0004"],
        "Protein ID": ["P0001", "P0002", "P0003", "P0004"],
        "Entry Name": ["A_YEAST", "B_YEAST", "C_ECOLI", "D_HUMAN"],
        "Gene": ["GEN1", "GEN2", "GEN3", "GEN4"],
        "Protein Length": [300, 400, 250, 500],
        "Organism": ["Yeast", "Yeast", "E. coli", "Homo sapiens"],
        "Protein Existence": ["Evidence at protein level"] * 4,
        "Description": ["Prot A", "Prot B", "Prot C", "Prot D"],
        "Protein Probability": [0.99, 0.98, 0.97, 0.96],
        "Top Peptide Probability": [0.98, 0.97, 0.96, 0.95],
        "Total Peptides": [5, 6, 7, 8],
        "Spectral Count": [20, 25, 30, 35],
        "Unique Spectral Count": [10, 12, 14, 16],
        "Total Spectral Count": [25, 30, 35, 40],
        "Indistinguishable Proteins": ["", "", "", ""],
    }
    for col in COND_A:
        data[col] = [10.0, 12.0, 14.0, 16.0]
    for col in COND_B:
        data[col] = [20.0, 22.0, 24.0, 26.0]
    return pd.DataFrame(data)


def _make_dataset_with_stats() -> pd.DataFrame:
    """Dataset that additionally carries p_value and fold_change columns."""
    df = _make_dataset()
    df[FC] = [-1.5, -0.3, 1.8, 0.1]  # Yeast↓, Yeast ns, E.coli↑, Human ns
    df[PVALUE] = [0.01, 0.4, 0.02, 0.6]
    return df


def _make_large_dataset_with_stats(n_rows: int = 200) -> pd.DataFrame:
    """Larger synthetic dataset for robust multiple-testing correction coverage."""
    organisms = ["Yeast", "E. coli", "Human"]
    rows = {
        PROTEIN: [f"P{i:05d}" for i in range(1, n_rows + 1)],
        PROTEIN_ID: [f"P{i:05d}" for i in range(1, n_rows + 1)],
        "Entry Name": [f"ENTRY_{i:05d}" for i in range(1, n_rows + 1)],
        "Gene": [f"GENE_{i:05d}" for i in range(1, n_rows + 1)],
        "Protein Length": [250 + (i % 500) for i in range(n_rows)],
        ORGANISM: [organisms[i % len(organisms)] for i in range(n_rows)],
        "Protein Existence": ["Evidence at protein level"] * n_rows,
        "Description": ["Synthetic protein"] * n_rows,
        "Protein Probability": np.linspace(0.90, 0.999, n_rows),
        "Top Peptide Probability": np.linspace(0.85, 0.995, n_rows),
        TOT_PEP: [2 + (i % 6) for i in range(n_rows)],
        "Spectral Count": [10 + (i % 50) for i in range(n_rows)],
        "Unique Spectral Count": [5 + (i % 25) for i in range(n_rows)],
        "Total Spectral Count": [15 + (i % 60) for i in range(n_rows)],
        "Indistinguishable Proteins": [""] * n_rows,
        FC: np.linspace(-3.0, 3.0, n_rows),
        PVALUE: np.linspace(0.001, 0.999, n_rows),
    }
    for j, col in enumerate(COND_A, start=1):
        rows[col] = np.linspace(8.0 + j, 80.0 + j, n_rows)
    for j, col in enumerate(COND_B, start=1):
        rows[col] = np.linspace(9.0 + j, 82.0 + j, n_rows)
    return pd.DataFrame(rows)


def _make_param_table() -> pd.DataFrame:
    """ParameterTable.csv mock whose single row matches the default spectral-search params."""
    return pd.DataFrame(
        {
            "tool": ["fragpipe"],
            "match_between_runs": ["FALSE"],
            "precursor_mass_tolerance": [5],
            "fragment_mass_tolerance": ["0.01"],
            "enzyme": ["stricttrypsin"],
            "missed_cleavages": [1],
            "min_peptide_length": [7],
            "max_peptide_length": [35],
            "ParameterSet": ["ParameterSet_001"],
        }
    )


def _load_station_options() -> dict:
    """Load station parameter options from frontend/stations.json."""
    stations_path = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "assets"
        / "stations.json"
    )
    with stations_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_bounded_combinations(
    option_map: dict[str, list], cap: int = _MAX_CONFIG_CASES
) -> list[dict]:
    """Return up to `cap` deterministic parameter combinations from an option map."""
    keys = list(option_map.keys())
    values = [option_map[key] for key in keys]
    combos = []
    for parts in itertools.product(*values):
        combos.append(dict(zip(keys, parts)))
        if len(combos) >= cap:
            break
    return combos


def _to_backend_param_type(param_name: str, value):
    """Convert frontend-config option strings to backend expected input types."""
    if param_name in {
        "precursor_mass_tolerance",
        "missed_cleavages",
        "min_peptide_length",
        "max_peptide_length",
        "remove_missing_proteins",
        "min_peptides_per_protein",
    }:
        return int(value)
    return value


def _build_param_table_from_combinations(combos: list[dict]) -> pd.DataFrame:
    """Build a ParameterTable-like DataFrame matching provided spectral-search combos."""
    rows = []
    for idx, combo in enumerate(combos, start=1):
        row = {
            "tool": combo["tool"],
            "match_between_runs": str(combo["match_between_runs"]).upper(),
            "precursor_mass_tolerance": int(combo["precursor_mass_tolerance"]),
            "fragment_mass_tolerance": str(combo["fragment_mass_tolerance"]),
            "enzyme": combo["enzyme"],
            "missed_cleavages": int(combo["missed_cleavages"]),
            "min_peptide_length": int(combo["min_peptide_length"]),
            "max_peptide_length": int(combo["max_peptide_length"]),
            "ParameterSet": f"ParameterSet_{idx:03d}",
        }
        rows.append(row)
    return pd.DataFrame(rows)


class TestEnterStationPrerequisites(TestCase):
    def test_returns_feedback_when_required_station_missing(self):
        user = get_user_model().objects.create_user(username="entry_guard_user")
        self.client.force_login(user)

        response = self.client.post("/api/stations/mass_spec/enter/", data={})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["missing_station_id"], "sample_prep")
        self.assertIn("Do sample prep first", payload["feedback"])

    def test_allows_entry_when_requirement_is_satisfied(self):
        user = get_user_model().objects.create_user(username="entry_ok_user")
        StationRun.objects.create(
            player=user, station_id="sample_prep", params={}, score=0
        )
        self.client.force_login(user)

        response = self.client.post("/api/stations/mass_spec/enter/", data={})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["station_id"], "mass_spec")


# ---------------------------------------------------------------------------
# Station: sample_prep
# ---------------------------------------------------------------------------


class TestSamplePrepStation(TestCase):
    def test_always_succeeds(self):
        result = _simulate_sample_prep(None, {})
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 0)
        self.assertIn("feedback", result)


# ---------------------------------------------------------------------------
# Station: mass_spec
# ---------------------------------------------------------------------------


class TestMassSpecStation(TestCase):
    def test_success_after_sample_prep(self):
        result = _simulate_mass_spec(None, {})
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 0)


# ---------------------------------------------------------------------------
# Station: spectral_search
# ---------------------------------------------------------------------------


_DEFAULT_SPECTRAL_PARAMS = {
    "tool": "fragpipe",
    "match_between_runs": "FALSE",
    "precursor_mass_tolerance": 5,
    "fragment_mass_tolerance": "0.01",
    "enzyme": "stricttrypsin",
    "missed_cleavages": 1,
    "min_peptide_length": 7,
    "max_peptide_length": 35,
}


class TestSpectralSearchStation(TestCase):
    def test_raises_for_unknown_params(self):
        # No matching row in the parameter table → ValueError
        with patch("game.services.pd.read_csv", return_value=_make_param_table()):
            with self.assertRaises(ValueError):
                _simulate_spectral_search(
                    None,
                    {"tool": "unknown_tool"},
                )

    @patch("game.services._create_histogram", return_value=_DUMMY_IMG)
    def test_success_with_default_params(self, _mock_hist):
        def _read_csv_side_effect(path, *args, **kwargs):
            if "ParameterTable" in str(path):
                return _make_param_table()
            return _make_dataset()

        with patch("game.services.pd.read_csv", side_effect=_read_csv_side_effect):
            result = _simulate_spectral_search(None, _DEFAULT_SPECTRAL_PARAMS)

        self.assertTrue(result["success"])
        self.assertIn("num_prot", result)
        self.assertIsInstance(result["img"], list)


# ---------------------------------------------------------------------------
# Station: data_review
# ---------------------------------------------------------------------------


class TestDataReviewStation(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_data_review(pd.DataFrame(), {})
        self.assertFalse(result["success"])
        self.assertIn("spectral search", result["feedback"].lower())

    def test_returns_metrics_and_preview_for_dataset(self):
        result = _simulate_data_review(_make_dataset_with_stats(), {})
        self.assertTrue(result["success"])
        self.assertIn("metric_cards", result)
        self.assertIn("table_preview", result)
        self.assertEqual(result["table_preview"]["shown_rows"], 4)
        self.assertEqual(result["table_preview"]["total_rows"], 4)
        self.assertEqual(len(result["sample_metrics"]), len(COND_A) + len(COND_B))
        self.assertTrue(
            any(
                metric["label"] == "Significant proteins"
                for metric in result["metric_cards"]
            )
        )
        self.assertTrue(
            any(
                item["column"] == "Protein Probability"
                for item in result["column_explanations"]
            )
        )
        self.assertTrue(
            any(
                item["column"] == "Sample intensity columns"
                for item in result["column_explanations"]
            )
        )

    def test_returns_full_table_for_browsing(self):
        large_dataset = pd.concat([_make_dataset()] * 8, ignore_index=True)
        result = _simulate_data_review(large_dataset, {})
        self.assertTrue(result["success"])
        self.assertEqual(result["table_preview"]["shown_rows"], len(large_dataset))
        self.assertEqual(result["table_preview"]["columns"], list(large_dataset.columns))
        self.assertEqual(len(result["table_preview"]["rows"]), len(large_dataset))
        self.assertEqual(
            result["table_preview"]["rows"][0],
            [_to_json_safe(value) for value in large_dataset.iloc[0].tolist()],
        )


class TestDataReviewApi(TestCase):
    def test_run_station_endpoint_returns_full_table_rows_and_columns(self):
        user = get_user_model().objects.create_user(username="data_review_api_user")
        self.client.force_login(user)

        dataset = _make_large_dataset_with_stats(n_rows=200)
        session = self.client.session
        session["current_dataset"] = DataFrameSessionSerializer.dumps(dataset)
        session.save()

        response = self.client.post(
            "/api/stations/data_review/run/",
            data=json.dumps({"params": {}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["table_preview"]["shown_rows"], len(dataset))
        self.assertEqual(payload["table_preview"]["total_rows"], len(dataset))
        self.assertEqual(payload["table_preview"]["columns"], list(dataset.columns))
        self.assertEqual(len(payload["table_preview"]["rows"]), len(dataset))
        self.assertEqual(
            payload["table_preview"]["rows"][0],
            [_to_json_safe(value) for value in dataset.iloc[0].tolist()],
        )


# ---------------------------------------------------------------------------
# Station: transform
# ---------------------------------------------------------------------------


class TestTransformStation(TestCase):
    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_log2_transformation(self, _mock_bp):
        df = _make_dataset()
        result = _simulate_transform(df, {"transform_method": "log2"})
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        self.assertAlmostEqual(
            result["dataset"][COND_A[0]].iloc[0], np.log2(10.0), places=5
        )

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_natural_log_transformation(self, _mock_bp):
        df = _make_dataset()
        result = _simulate_transform(df, {"transform_method": "ln"})
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        self.assertAlmostEqual(
            result["dataset"][COND_B[0]].iloc[0], np.log(20.0), places=5
        )

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_unknown_method_fails(self, _mock_bp):
        result = _simulate_transform(_make_dataset(), {"transform_method": "sqrt"})
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Station: filtering
# ---------------------------------------------------------------------------


class TestFilteringStation(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_filtering(pd.DataFrame(), {})
        self.assertFalse(result["success"])

    @patch("game.services.filtering_piechart", return_value=_DUMMY_IMG)
    @patch("game.services.filtering_scatterplot", return_value=_DUMMY_IMG)
    def test_filters_proteins_by_missing_threshold(self, _mock_sc, _mock_pie):
        # NOTE: this test will fail until the typo 'zmissing_num' in services.py
        # is corrected to 'missing_num'.
        df = _make_dataset()
        result = _simulate_filtering(
            df,
            {"remove_missing_proteins": 6, "min_peptides_per_protein": 1},
        )
        self.assertTrue(result["success"])
        self.assertIn("num_pro", result)


# ---------------------------------------------------------------------------
# Station: normalize
# ---------------------------------------------------------------------------


class TestNormalizeStation(TestCase):
    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_no_normalization(self, _mock_hc):
        result = _simulate_normalize(_make_dataset(), {"normalization": "none"})
        self.assertTrue(result["success"])

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_median_normalization(self, _mock_hc):
        df = _make_dataset()
        result = _simulate_normalize(df, {"normalization": "median"})
        self.assertTrue(result["success"])
        # After median normalization each column should be centered near zero
        col = COND_A[0]
        self.assertAlmostEqual(result["dataset"][col].median(), 0.0, places=5)

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_zscore_normalization(self, _mock_hc):
        result = _simulate_normalize(_make_dataset(), {"normalization": "zscore"})
        self.assertTrue(result["success"])

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_unknown_method_fails(self, _mock_hc):
        result = _simulate_normalize(_make_dataset(), {"normalization": "magic"})
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Station: imputer
# ---------------------------------------------------------------------------


class TestImputer(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_imputer(pd.DataFrame(), {})
        self.assertFalse(result["success"])

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_no_imputation(self, _mock_plot):
        df = _make_dataset()
        result = _simulate_imputer(df, {"imputation_method": "none"})
        self.assertTrue(result["success"])
        # Values must remain unchanged
        pd.testing.assert_frame_equal(
            result["dataset"][COND_A + COND_B], df[COND_A + COND_B]
        )

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_mean_imputation_fills_nans(self, _mock_plot):
        df = _make_dataset()
        df.loc[0, COND_A[0]] = np.nan  # introduce one missing value
        result = _simulate_imputer(df, {"imputation_method": "mean"})
        self.assertTrue(result["success"])
        self.assertFalse(result["dataset"][COND_A[0]].isna().any())

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_minprob_imputation(self, _mock_plot):
        df = _make_dataset()
        df.loc[0, COND_B[1]] = np.nan
        result = _simulate_imputer(df, {"imputation_method": "minprob"})
        self.assertTrue(result["success"])
        self.assertFalse(result["dataset"][COND_B[1]].isna().any())


# ---------------------------------------------------------------------------
# Station: multiple_testing_corrector
# ---------------------------------------------------------------------------


class TestMultipleTestingCorrectorStation(TestCase):
    def test_fails_without_pvalue_column(self):
        result = _simulate_multiple_testing_corrector(_make_dataset(), {})
        self.assertFalse(result["success"])

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_benjamini_hochberg_correction(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(df, {"correction_method": "bh"})
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        # Adjusted p-values should remain in [0, 1]
        self.assertTrue((result["dataset"][PVALUE] <= 1.0).all())

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_bonferroni_correction(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(
            df, {"correction_method": "bonferroni"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 6)

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_unknown_correction_fails(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(
            df, {"correction_method": "magic"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_nan_pvalues_are_preserved_after_correction(self, _mock_hist):
        """MTC must not corrupt valid p-values when the input contains NaNs.

        Proteins that could not be tested (e.g. too few replicates) receive NaN
        p-values from statistical_analysis. multipletests() cannot handle NaN
        inputs so we must apply correction only to finite values and leave NaN
        positions untouched.
        """
        df = _make_large_dataset_with_stats()
        # Inject NaNs into the middle of the p-value column (simulating proteins
        # that had no valid test statistic).
        df.loc[10:50, PVALUE] = np.nan
        n_valid_before = df[PVALUE].notna().sum()

        result = _simulate_multiple_testing_corrector(df, {"correction_method": "bh"})

        self.assertTrue(result["success"])
        out = result["dataset"]
        n_valid_after = out[PVALUE].notna().sum()
        # The number of valid (non-NaN) corrected values must equal the number of
        # valid input p-values — NaN rows must remain NaN, valid rows must be corrected.
        self.assertEqual(
            n_valid_after,
            n_valid_before,
            f"Expected {n_valid_before} valid corrected p-values, got {n_valid_after}",
        )
        corrected = out[PVALUE].dropna()
        self.assertTrue((corrected >= 0).all() and (corrected <= 1).all())

    def test_mtc_pvalues_valid_after_welch_pipeline_with_nans(self):
        """MTC must not wipe out valid p-values when input contains NaN entries.

        The key regression: multipletests() called on an array with NaNs returned
        all-NaN adjusted values, making every histogram empty.
        """
        df = _make_large_dataset_with_stats()
        # Simulate what statistical_analysis produces: some NaN p-values mixed with valid ones
        df.loc[::5, PVALUE] = np.nan  # every 5th protein has no p-value
        n_valid_before = df[PVALUE].notna().sum()

        with patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG]):
            result = _simulate_multiple_testing_corrector(
                df, {"correction_method": "bh"}
            )

        self.assertTrue(result["success"])
        out = result["dataset"]
        n_valid_after = out[PVALUE].notna().sum()
        self.assertEqual(
            n_valid_after,
            n_valid_before,
            f"Expected {n_valid_before} valid p-values after MTC but got {n_valid_after} — "
            "NaN handling in multipletests() corrupted the output",
        )


# ---------------------------------------------------------------------------
# Station: the_cutter
# ---------------------------------------------------------------------------


class TestTheCutterStation(TestCase):
    def test_fails_without_fc_column(self):
        result = _simulate_the_cutter(_make_dataset(), {})
        self.assertFalse(result["success"])

    @patch("game.services.plot_significant_proteins", return_value=_DUMMY_IMG)
    def test_cutoff_filters_correctly(self, _mock_plot):
        df = _make_dataset_with_stats()
        # FC cutoff 1.0, p-value cutoff 0.05 → keeps rows with |FC|>=1 and p<=0.05
        result = _simulate_the_cutter(
            df,
            {"fold_change_cutoff": 1.0, "pvalue_cutoff": 0.05},
        )
        self.assertEqual(result["score"], 0)
        # Expect 2 significant proteins: P0001 (FC=-1.5, p=0.01) and P0003 (FC=1.8, p=0.02)
        self.assertEqual(len(result["dataset"]), 2)

    @patch("game.services.plot_significant_proteins", return_value=_DUMMY_IMG)
    def test_no_candidates_with_strict_cutoff(self, _mock_plot):
        df = _make_dataset_with_stats()
        result = _simulate_the_cutter(
            df,
            {"fold_change_cutoff": 5.0, "pvalue_cutoff": 0.001},
        )
        self.assertEqual(len(result["dataset"]), 0)


# ---------------------------------------------------------------------------
# Station: statistical_analysis
# ---------------------------------------------------------------------------


class TestStatisticalAnalysisStation(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_statistical_analysis(
            pd.DataFrame(), {"statistical_test": "welch"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_welch_ttest_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(df, {"statistical_test": "welch"})
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)
        self.assertIn(FC, result["dataset"].columns)
        # p-values must be in [0, 1] or NaN
        pvals = result["dataset"][PVALUE].dropna()
        self.assertTrue((pvals >= 0).all() and (pvals <= 1).all())

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_mannwhitneyu_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(
            df, {"statistical_test": "mannwhitneyu"}
        )
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_limma_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(df, {"statistical_test": "limma"})
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)
        self.assertIn(FC, result["dataset"].columns)
        pvals = result["dataset"][PVALUE].dropna()
        self.assertTrue((pvals >= 0).all() and (pvals <= 1).all())

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_limma_includes_proteins_with_missing_values(self, _mock_vp):
        """Proteins that lose some replicates to NaN but still have ≥1 per group
        should receive a p-value rather than being silently dropped.

        A larger dataset (30 proteins) is used so the empirical Bayes prior is
        estimated reliably and the NaN-heavy protein can borrow variance from it.
        """
        n = 30
        rng = np.random.default_rng(42)
        base_df = _make_large_dataset_with_stats(n_rows=n)
        # Replace intensity columns with random, non-zero-variance values
        for col in COND_A:
            base_df[col] = rng.normal(loc=10.0, scale=1.5, size=n)
        for col in COND_B:
            base_df[col] = rng.normal(loc=15.0, scale=1.5, size=n)
        # Strip protein 0 down to 1 valid replicate per group (df_g = 0):
        # only COND_A[0] / COND_B[0] remain; [1] and [2] are set to NaN.
        base_df.loc[0, COND_A[1]] = np.nan
        base_df.loc[0, COND_A[2]] = np.nan
        base_df.loc[0, COND_B[1]] = np.nan
        base_df.loc[0, COND_B[2]] = np.nan
        result = _simulate_statistical_analysis(base_df, {"statistical_test": "limma"})
        self.assertTrue(result["success"])
        # The NaN-heavy protein must still get a p-value (prior variance covers it)
        p0 = result["dataset"].loc[0, PVALUE]
        self.assertTrue(
            np.isfinite(p0),
            f"Expected finite p-value for NaN-heavy protein, got {p0}",
        )

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_unknown_test_fails(self, _mock_vp):
        result = _simulate_statistical_analysis(
            _make_dataset(), {"statistical_test": "magic"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_sam_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(df, {"statistical_test": "sam"})
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)
        self.assertIn(FC, result["dataset"].columns)
        pvals = result["dataset"][PVALUE].dropna()
        self.assertTrue((pvals >= 0).all() and (pvals <= 1).all())


class TestSqueezeVar(TestCase):
    """Unit tests for the _squeeze_var empirical Bayes helper."""

    def test_returns_finite_squeezed_variances(self):
        rng = np.random.default_rng(0)
        n = 20
        sample_vars = rng.exponential(scale=2.0, size=n)
        dfs = np.full(n, 4.0)
        squeezed, df_prior = _squeeze_var(sample_vars, dfs)
        self.assertEqual(len(squeezed), n)
        self.assertTrue(np.all(np.isfinite(squeezed)))
        self.assertGreaterEqual(df_prior, 0.0)

    def test_nan_proteins_get_prior_variance(self):
        """Proteins with NaN sample_var (df=0) should receive the prior variance."""
        sample_vars = np.array([1.0, 2.0, 3.0, np.nan, np.nan])
        dfs = np.array([4.0, 4.0, 4.0, 0.0, 0.0])
        squeezed, _ = _squeeze_var(sample_vars, dfs)
        self.assertTrue(np.isfinite(squeezed[3]))
        self.assertTrue(np.isfinite(squeezed[4]))

    def test_shrinks_extreme_variances_toward_center(self):
        """Highly variable per-protein variances should be pulled toward the center."""
        sample_vars = np.array([0.01, 0.01, 100.0, 100.0])
        dfs = np.full(4, 4.0)
        squeezed, _ = _squeeze_var(sample_vars, dfs)
        # Squeezed low variance should be above raw; squeezed high variance below raw
        self.assertGreater(squeezed[0], sample_vars[0])
        self.assertLess(squeezed[2], sample_vars[2])


class TestSamGroundTruth(TestCase):
    """Ground-truth tests for the SAM end-to-end path with known data."""

    def _run_sam(self, df):
        with patch("game.services.volcano_plot", return_value="img"):
            return _simulate_statistical_analysis(df, {"statistical_test": "sam"})

    def _make_clear_df(self):
        """20-protein dataset where protein 0 is strongly UP and protein 19 is
        strongly DOWN (completely reversed ordering between A and B).
        Proteins 9 and 10 are the middle proteins with no consistent direction.
        Each protein has a small random spread so variances are non-zero.
        """
        rng = np.random.default_rng(0)
        n = 20
        a_vals = np.arange(1.0, n + 1)
        b_vals = np.arange(float(n), 0.0, -1.0)
        base = {
            "Protein": [f"P{i:03d}" for i in range(n)],
            "Protein ID": [f"P{i:03d}" for i in range(n)],
            "Entry Name": [f"E{i:03d}" for i in range(n)],
            "Gene": [f"G{i:03d}" for i in range(n)],
            "Protein Length": [300] * n,
            "Organism": ["Yeast"] * n,
            "Protein Existence": ["Evidence at protein level"] * n,
            "Description": ["Protein"] * n,
            "Protein Probability": [0.99] * n,
            "Top Peptide Probability": [0.98] * n,
            "Total Peptides": [5] * n,
            "Spectral Count": [20] * n,
            "Unique Spectral Count": [10] * n,
            "Total Spectral Count": [25] * n,
            "Indistinguishable Proteins": [""] * n,
        }
        noise = rng.normal(0, 0.1, size=(n, len(COND_A) + len(COND_B)))
        for j, col in enumerate(COND_A):
            base[col] = a_vals + noise[:, j]
        for j, col in enumerate(COND_B):
            base[col] = b_vals + noise[:, len(COND_A) + j]
        return pd.DataFrame(base)

    def test_upregulated_protein_gets_smaller_pvalue_than_null(self):
        """P0 (lowest in A, highest in B) must be more significant than P9 (middle)."""
        df = self._make_clear_df()
        result = self._run_sam(df)
        self.assertTrue(result["success"])
        pvals = result["dataset"][PVALUE]
        p_up = pvals.iloc[0]  # P0: strongly upregulated
        p_null = pvals.iloc[9]  # P9: middle, no consistent direction
        self.assertTrue(np.isfinite(p_up))
        self.assertTrue(np.isfinite(p_null))
        self.assertLess(
            p_up,
            p_null,
            f"Upregulated protein p={p_up:.4f} should be < null p={p_null:.4f}",
        )

    def test_downregulated_protein_gets_smaller_pvalue_than_null(self):
        """P19 (highest in A, lowest in B) must be more significant than P10 (middle)."""
        df = self._make_clear_df()
        result = self._run_sam(df)
        pvals = result["dataset"][PVALUE]
        p_down = pvals.iloc[19]  # P19: strongly downregulated
        p_null = pvals.iloc[10]  # P10: middle
        self.assertTrue(np.isfinite(p_down))
        self.assertLess(
            p_down,
            p_null,
            f"Downregulated protein p={p_down:.4f} should be < null p={p_null:.4f}",
        )


# ---------------------------------------------------------------------------
# Station: final_report (final scoring station)
# ---------------------------------------------------------------------------


class TestFinalReportStation(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_final_report(pd.DataFrame(), {})
        self.assertFalse(result["success"])

    def test_counts_true_and_false_positives(self):
        with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
            df = _make_dataset_with_stats()
            # Yeast P0001 has FC=-1.5 → true positive; E.coli P0003 has FC=1.8 → true positive
            # Yeast P0002 has FC=-0.3 → true positive (FC < 0); Human P0004 → false positive
            result = _simulate_final_report(df, {})
        self.assertEqual(
            result["true_positives"], 3
        )  # P0001+P0002 (Yeast FC<0) + P0003 (E.coli FC>0)
        self.assertEqual(result["false_positives"], 1)  # P0004 Human
        self.assertGreater(result["score"], 0)
        self.assertIn("Final score breakdown", result["feedback"])

    def test_score_is_zero_for_all_false_positives(self):
        with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
            # All Human → all false positives
            df = _make_dataset_with_stats()
            df[ORGANISM] = "Homo sapiens"
            result = _simulate_final_report(df, {})
        self.assertEqual(result["score"], 0)

    def test_score_increases_with_more_true_positives(self):
        with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
            low_tp_df = pd.DataFrame(
                {
                    ORGANISM: ["Yeast", "Homo sapiens"],
                    FC: [-1.0, 0.2],
                }
            )
            high_tp_df = pd.DataFrame(
                {
                    ORGANISM: [
                        "Yeast",
                        "Yeast",
                        "Yeast",
                        "Yeast",
                        "Yeast",
                        "E. coli",
                        "E. coli",
                        "E. coli",
                        "E. coli",
                        "E. coli",
                        "Homo sapiens",
                    ],
                    FC: [-1.0, -1.2, -0.5, -0.9, -1.4, 0.6, 1.0, 0.8, 1.3, 0.4, 0.2],
                }
            )

            low_tp_result = _simulate_final_report(low_tp_df, {})
            high_tp_result = _simulate_final_report(high_tp_df, {})

        self.assertEqual(low_tp_result["false_positives"], 1)
        self.assertEqual(high_tp_result["false_positives"], 1)
        self.assertGreater(
            high_tp_result["true_positives"], low_tp_result["true_positives"]
        )
        self.assertGreater(high_tp_result["score"], low_tp_result["score"])


# ---------------------------------------------------------------------------
# Parameter-configuration coverage tests
# ---------------------------------------------------------------------------


class TestStationParameterConfigurations(TestCase):
    """
    Cover every station parameter configuration from frontend stations.json.
    If total combinations exceed 10, run only the first 10 deterministic combos.
    """

    def setUp(self):
        self.station_options = _load_station_options()

    @patch("game.services._create_histogram", return_value=_DUMMY_IMG)
    def test_spectral_search_parameter_configurations(self, _mock_hist):
        params_cfg = self.station_options["spectral_search"]["parameters"]
        option_map = {p["id"]: p["options"] for p in params_cfg}
        combos = _build_bounded_combinations(option_map)
        param_table = _build_param_table_from_combinations(combos)

        def _read_csv_side_effect(path, *args, **kwargs):
            if "ParameterTable" in str(path):
                return param_table
            return _make_dataset()

        with patch("game.services.pd.read_csv", side_effect=_read_csv_side_effect):
            for combo in combos:
                with self.subTest(combo=combo):
                    backend_params = {
                        key: _to_backend_param_type(key, value)
                        for key, value in combo.items()
                    }
                    result = _simulate_spectral_search(
                        None,
                        backend_params,
                    )
                    self.assertTrue(result["success"])
                    self.assertIsInstance(result["dataset"], pd.DataFrame)

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_transform_parameter_configurations(self, _mock_bp):
        options = self.station_options["transform"]["parameters"][0]["options"]
        for method in options:
            with self.subTest(transform_method=method):
                result = _simulate_transform(
                    _make_dataset(), {"transform_method": method}
                )
                self.assertTrue(result["success"])

    @patch("game.services.filtering_piechart", return_value=_DUMMY_IMG)
    @patch("game.services.filtering_scatterplot", return_value=_DUMMY_IMG)
    def test_filtering_parameter_configurations(self, _mock_sc, _mock_pie):
        params_cfg = self.station_options["filtering"]["parameters"]
        option_map = {p["id"]: p["options"] for p in params_cfg}
        combos = _build_bounded_combinations(option_map)

        for combo in combos:
            with self.subTest(combo=combo):
                backend_params = {
                    key: _to_backend_param_type(key, value)
                    for key, value in combo.items()
                }
                input_df = _make_dataset()
                result = _simulate_filtering(
                    input_df,
                    backend_params,
                )
                self.assertTrue(result["success"])
                self.assertIn("dataset", result)
                self.assertIsInstance(result["dataset"], pd.DataFrame)
                self.assertLessEqual(len(result["dataset"]), len(input_df))

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_normalize_parameter_configurations(self, _mock_hc):
        options = self.station_options["normalize"]["parameters"][0]["options"]
        for method in options:
            with self.subTest(normalization=method):
                result = _simulate_normalize(_make_dataset(), {"normalization": method})
                self.assertTrue(result["success"])

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_imputer_parameter_configurations(self, _mock_plot):
        options = self.station_options["imputer"]["parameters"][0]["options"]
        for method in options:
            with self.subTest(imputation_method=method):
                dataset = _make_dataset()
                dataset.loc[0, COND_A[0]] = np.nan
                result = _simulate_imputer(
                    dataset,
                    {"imputation_method": method},
                )
                self.assertTrue(result["success"])

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_multiple_testing_parameter_configurations(self, _mock_hist):
        options = self.station_options["multiple_testing_corrector"]["parameters"][0][
            "options"
        ]
        large_df = _make_large_dataset_with_stats()
        for method in options:
            with self.subTest(correction_method=method):
                result = _simulate_multiple_testing_corrector(
                    large_df.copy(),
                    {"correction_method": method},
                )
                self.assertTrue(result["success"])
                self.assertIn(PVALUE, result["dataset"].columns)
                corrected = result["dataset"][PVALUE].dropna()
                self.assertTrue((corrected >= 0).all())
                self.assertTrue((corrected <= 1).all())

    @patch("game.services.plot_significant_proteins", return_value=_DUMMY_IMG)
    def test_the_cutter_parameter_configurations(self, _mock_sig):
        # Slider parameters are continuous; test representative grid with cap 10.
        fold_changes = list(range(0, 8))
        pvals = [0.0, 0.01, 0.05, 0.5, 1.0]
        combos = []
        for fc_cut, p_cut in itertools.product(fold_changes, pvals):
            combos.append({"fold_change_cutoff": fc_cut, "pvalue_cutoff": p_cut})
            if len(combos) >= _MAX_CONFIG_CASES:
                break

        for combo in combos:
            with self.subTest(combo=combo):
                result = _simulate_the_cutter(
                    _make_dataset_with_stats(),
                    combo,
                )
                self.assertIn("dataset", result)
                self.assertIsInstance(result["dataset"], pd.DataFrame)

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_statistical_analysis_parameter_configurations(self, _mock_vp):
        options = self.station_options["statistical_analysis"]["parameters"][0][
            "options"
        ]
        expected_success = {
            "welch": True,
            "limma": True,
            "mannwhitneyu": True,
            "permutation": True,
            "sam": True,
        }
        for test_name in options:
            with self.subTest(statistical_test=test_name):
                result = _simulate_statistical_analysis(
                    _make_dataset(),
                    {"statistical_test": test_name},
                )
                self.assertEqual(result["success"], expected_success[test_name])


# ---------------------------------------------------------------------------
# Full workflow integration test (moved below all imports)
# ---------------------------------------------------------------------------


class TestFullWorkflowIntegration(TestCase):
    def test_full_workflow_default_parameters(self):
        """Run the full workflow of all stations with default parameters and report protein numbers and score."""
        import pandas as pd
        from unittest.mock import patch
        from game.services import DATA_DIR, PROTEIN

        # Helper to print protein stats
        def print_stats(stage, df):
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                print(f"{stage}: No data")
            else:
                print(
                    f"{stage}: n_rows={len(df)}, n_unique_proteins={df[PROTEIN].nunique() if PROTEIN in df.columns else 'NA'}"
                )

        # Patch pd.read_csv so that spectral_search loads the real ParameterSet_001.tsv
        orig_read_csv = pd.read_csv

        def patched_read_csv(path, *args, **kwargs):
            path_str = str(path)
            if path_str.endswith("ParameterTable.csv"):
                return orig_read_csv(DATA_DIR / "ParameterTable.csv", *args, **kwargs)
            if path_str.endswith("ParameterSet_001.tsv"):
                return orig_read_csv(DATA_DIR / "ParameterSet_001.tsv", *args, **kwargs)
            return orig_read_csv(path, *args, **kwargs)

        with patch("pandas.read_csv", side_effect=patched_read_csv):
            df = None

            # Sample prep
            result = _simulate_sample_prep(df, {})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("sample_prep", df)

            # Mass spec
            result = _simulate_mass_spec(df, {})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("mass_spec", df)

            # Spectral search (simulate default params)
            result = _simulate_spectral_search(df, {})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("spectral_search", df)

            # Transform
            result = _simulate_transform(df, {"transform_method": "ln"})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("transform", df)

            # Filtering
            result = _simulate_filtering(
                df, {"remove_missing_proteins": 0, "min_peptides_per_protein": 1}
            )
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("filtering", df)

            # Normalize
            result = _simulate_normalize(df, {"normalization": "none"})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("normalize", df)

            # Imputer
            result = _simulate_imputer(df, {"imputation_method": "none"})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("imputer", df)

            # Statistical analysis (Welch's t-test)
            result = _simulate_statistical_analysis(df, {"statistical_test": "welch"})
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("statistical_analysis", df)

            # Multiple testing correction (Benjamini-Hochberg)
            result = _simulate_multiple_testing_corrector(
                df, {"correction_method": "bh"}
            )
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("multiple_testing_corrector", df)

            # The cutter (default cutoffs)

            result = _simulate_the_cutter(
                df, {"fold_change_cutoff": 1, "pvalue_cutoff": 0.05}
            )
            if "success" not in result:
                print("the_cutter result (no 'success' key):", result)
                self.fail(
                    "the_cutter did not return a 'success' key. See printed result above."
                )
            self.assertTrue(result["success"])
            df = result["dataset"]
            print_stats("the_cutter", df)

            # Final report
            with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
                result = _simulate_final_report(df, {})
            self.assertTrue(result["success"])
            print("\nFull workflow outcome:")
            print(f"Number of proteins in final set: {len(df)}")
            print(f"Final score: {result['score']}")
            print(
                f"True positives: {result['true_positives']}, False positives: {result['false_positives']}"
            )


# ---------------------------------------------------------------------------
# Full end-to-end workflow integration test
# ---------------------------------------------------------------------------


def _read_csv_for_spectral_search(path, *args, **kwargs):
    """Side-effect for pd.read_csv: returns the ParameterTable or a real dataset."""
    if "ParameterTable" in str(path):
        return _make_param_table()
    return _make_dataset()


@patch("game.services.plot_scores", return_value=_DUMMY_IMG)
@patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
@patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
@patch("game.services.plot_significant_proteins", return_value=_DUMMY_IMG)
@patch("game.services.filtering_scatterplot", return_value=_DUMMY_IMG)
@patch("game.services.filtering_piechart", return_value=_DUMMY_IMG)
@patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
@patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
@patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
@patch("game.services._create_histogram", return_value=_DUMMY_IMG)
@patch("game.services.pd.read_table", side_effect=_read_csv_for_spectral_search)
class TestFullWorkflow(TestCase):
    """
    Chains every station in the canonical pipeline order and verifies that data
    flows correctly from one station to the next, ending with a scored final_report result.

    Station order:
      sample_prep → mass_spec → spectral_search → transform → filtering →
      normalize → imputer → statistical_analysis → multiple_testing_corrector →
    the_cutter → final_report
    """

    def test_full_pipeline(
        self,
        _mock_csv,
        _mock_create_hist,
        _mock_boxplot,
        _mock_hc,
        _mock_imputer_plot,
        _mock_pie,
        _mock_sc,
        _mock_sig_prot,
        _mock_mtc,
        _mock_vol,
        _mock_scores,
    ):
        dataset = None

        # --- 1. sample_prep ---
        r = _simulate_sample_prep(dataset, {})
        self.assertTrue(r["success"], "sample_prep failed")
        dataset = r["dataset"]

        # --- 2. mass_spec ---
        r = _simulate_mass_spec(dataset, {})
        self.assertTrue(r["success"], "mass_spec failed")
        dataset = r["dataset"]

        # --- 3. spectral_search ---
        r = _simulate_spectral_search(dataset, _DEFAULT_SPECTRAL_PARAMS)
        self.assertTrue(r["success"], "spectral_search failed")
        self.assertIsInstance(r["dataset"], pd.DataFrame)
        self.assertFalse(r["dataset"].empty)
        dataset = r["dataset"]

        # --- 4. transform (log2) ---
        r = _simulate_transform(dataset, {"transform_method": "log2"})
        self.assertTrue(r["success"], "transform failed")
        dataset = r["dataset"]

        # --- 5. filtering ---
        r = _simulate_filtering(
            dataset,
            {"remove_missing_proteins": 6, "min_peptides_per_protein": 1},
        )
        self.assertTrue(r["success"], "filtering failed")
        self.assertIsNotNone(r["dataset"])
        self.assertFalse(r["dataset"].empty)
        dataset = r["dataset"]

        # --- 6. normalize (median) ---
        r = _simulate_normalize(dataset, {"normalization": "median"})
        self.assertTrue(r["success"], "normalize failed")
        dataset = r["dataset"]

        # --- 7. imputer (mean) ---
        r = _simulate_imputer(dataset, {"imputation_method": "mean"})
        self.assertTrue(r["success"], "imputer failed")
        dataset = r["dataset"]

        # --- 8. statistical_analysis (welch) ---
        r = _simulate_statistical_analysis(dataset, {"statistical_test": "welch"})
        self.assertTrue(r["success"], "statistical_analysis failed")
        self.assertIn(PVALUE, r["dataset"].columns)
        self.assertIn(FC, r["dataset"].columns)
        dataset = r["dataset"]

        # --- 9. multiple_testing_corrector (BH) ---
        r = _simulate_multiple_testing_corrector(dataset, {"correction_method": "bh"})
        self.assertTrue(r["success"], "multiple_testing_corrector failed")
        dataset = r["dataset"]

        # --- 10. the_cutter ---
        r = _simulate_the_cutter(
            dataset,
            {"fold_change_cutoff": 0.0, "pvalue_cutoff": 1.0},  # permissive: keep all
        )
        self.assertIsNotNone(r["dataset"])
        dataset = r["dataset"]

        # --- 11. final_report (final scoring) ---
        r = _simulate_final_report(dataset, {})
        self.assertTrue(r["success"], "final_report failed")
        self.assertIn("score", r)
        self.assertIn("true_positives", r)
        self.assertIn("false_positives", r)
        total = r["true_positives"] + r["false_positives"]
        self.assertEqual(total, len(dataset), "TP + FP should equal total candidates")


class TestRunStationAnonymousUser(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_request(self):
        request = self.factory.post("/api/stations/test_station/run/", data={})
        middleware = SessionMiddleware(lambda _request: None)
        middleware.process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        return request


# ---------------------------------------------------------------------------
# Management command: recalculate
# ---------------------------------------------------------------------------


def _fake_simulators(score_map: dict, true_positives: int = 0, false_positives: int = 0):
    """Build fake STATION_SIMULATORS entries that just echo back fixed scores/TP/FP."""

    def _make(station_id):
        def _sim(dataset, params):
            return {
                "success": True,
                "score": score_map[station_id],
                "dataset": dataset,
                "true_positives": true_positives,
                "false_positives": false_positives,
            }

        return _sim

    return {station_id: _make(station_id) for station_id in score_map}


class TestRecalculateCommand(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="recalc_user")

    def test_no_runs_reports_nothing_to_update(self):
        out = StringIO()
        call_command("recalculate", stdout=out)
        self.assertIn("No differences found", out.getvalue())

    def test_unchanged_score_is_not_reported_as_a_change(self):
        StationRun.objects.create(
            player=self.user, station_id="sample_prep", params={}, score=0
        )
        simulators = _fake_simulators({"sample_prep": 0})
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            call_command("recalculate", stdout=out)
        self.assertIn("1 unchanged", out.getvalue())
        self.assertIn("No differences found", out.getvalue())

    def test_score_change_is_reported_and_prompts_for_confirmation(self):
        run = StationRun.objects.create(
            player=self.user, station_id="sample_prep", params={}, score=99
        )
        simulators = _fake_simulators({"sample_prep": 0})
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            with patch("builtins.input", return_value="n") as mock_input:
                call_command("recalculate", stdout=out)
        mock_input.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.score, 99, "score must stay unchanged when aborted")
        output = out.getvalue()
        self.assertIn("Station run score changes", output)
        self.assertIn("99.0000", output)
        self.assertIn("Aborted", output)

    def test_score_change_is_applied_when_confirmed(self):
        run = StationRun.objects.create(
            player=self.user, station_id="sample_prep", params={}, score=99
        )
        simulators = _fake_simulators({"sample_prep": 42})
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            with patch("builtins.input", return_value="y"):
                call_command("recalculate", stdout=out)
        run.refresh_from_db()
        self.assertEqual(run.score, 42)
        self.assertIn("Updated 1 station run score", out.getvalue())

    def test_yes_flag_skips_confirmation_prompt(self):
        run = StationRun.objects.create(
            player=self.user, station_id="sample_prep", params={}, score=1
        )
        simulators = _fake_simulators({"sample_prep": 2})
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            with patch("builtins.input") as mock_input:
                call_command("recalculate", "--yes", stdout=out)
        mock_input.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.score, 2)

    def test_final_result_tp_fp_change_detected_and_applied(self):
        run = StationRun.objects.create(
            player=self.user, station_id="final_report", params={}, score=0.5
        )
        final_result = FinalStationResult.objects.create(
            station_run=run, true_positives=3, false_positives=1
        )
        simulators = _fake_simulators(
            {"final_report": 0.5}, true_positives=5, false_positives=2
        )
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            with patch("builtins.input", return_value="y"):
                call_command("recalculate", stdout=out)
        final_result.refresh_from_db()
        self.assertEqual(final_result.true_positives, 5)
        self.assertEqual(final_result.false_positives, 2)
        output = out.getvalue()
        self.assertIn("Final result changes", output)
        self.assertIn("Updated 0 station run score(s) and 1 final result(s)", output)

    def test_unchanged_final_result_is_not_reported_as_a_change(self):
        run = StationRun.objects.create(
            player=self.user, station_id="final_report", params={}, score=0.5
        )
        FinalStationResult.objects.create(
            station_run=run, true_positives=5, false_positives=2
        )
        simulators = _fake_simulators(
            {"final_report": 0.5}, true_positives=5, false_positives=2
        )
        out = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", simulators, clear=True):
            call_command("recalculate", stdout=out)
        self.assertIn("No differences found", out.getvalue())

    def test_unknown_station_id_is_skipped_with_warning(self):
        StationRun.objects.create(
            player=self.user, station_id="mystery_station", params={}, score=0
        )
        out = StringIO()
        err = StringIO()
        with patch.dict("game.services.STATION_SIMULATORS", {}, clear=True):
            call_command("recalculate", stdout=out, stderr=err)
        self.assertIn("unknown station", err.getvalue())
        self.assertIn("No differences found", out.getvalue())

    def test_dataset_is_threaded_between_consecutive_runs_in_order(self):
        calls = []

        def sim_a(dataset, params):
            calls.append(("a", dataset))
            return {"success": True, "score": 0, "dataset": "dataset-from-a"}

        def sim_b(dataset, params):
            calls.append(("b", dataset))
            return {"success": True, "score": 0, "dataset": "dataset-from-b"}

        StationRun.objects.create(player=self.user, station_id="a", params={}, score=0)
        StationRun.objects.create(player=self.user, station_id="b", params={}, score=0)

        with patch.dict(
            "game.services.STATION_SIMULATORS", {"a": sim_a, "b": sim_b}, clear=True
        ):
            call_command("recalculate", "--yes", stdout=StringIO())

        self.assertEqual(calls, [("a", None), ("b", "dataset-from-a")])

    def test_skip_repeated_runs_recalculates_scores_but_does_not_thread_dataset(self):
        calls = []

        def sim_a(dataset, params):
            calls.append(("a", dataset))
            return {"success": True, "score": params["score"], "dataset": "dataset-from-a"}

        def sim_b(dataset, params):
            calls.append(("b", dataset))
            return {"success": True, "score": 0, "dataset": "dataset-from-b"}

        run_a1 = StationRun.objects.create(
            player=self.user, station_id="a", params={"score": 1}, score=1
        )
        run_a2 = StationRun.objects.create(
            player=self.user, station_id="a", params={"score": 2}, score=2
        )
        run_a3 = StationRun.objects.create(
            player=self.user, station_id="a", params={"score": 3}, score=3
        )
        run_b = StationRun.objects.create(player=self.user, station_id="b", params={}, score=0)

        out = StringIO()
        with patch.dict(
            "game.services.STATION_SIMULATORS", {"a": sim_a, "b": sim_b}, clear=True
        ):
            call_command("recalculate", "--yes", "--skip-repeated-runs", stdout=out)

        # Every run is recalculated: each "a" run receives the dataset
        # preceding the consecutive group (None), since repeats' datasets are
        # not threaded within the group; only the last "a" run's dataset is
        # applied and threaded into "b".
        self.assertEqual(
            calls,
            [
                ("a", None),
                ("a", None),
                ("a", None),
                ("b", "dataset-from-a"),
            ],
        )

        # All scores were recalculated and applied.
        run_a1.refresh_from_db()
        run_a2.refresh_from_db()
        run_a3.refresh_from_db()
        run_b.refresh_from_db()
        self.assertEqual(run_a1.score, 1)
        self.assertEqual(run_a2.score, 2)
        self.assertEqual(run_a3.score, 3)
        self.assertEqual(run_b.score, 0)

        # The repeated runs are reported as skipped for dataset threading.
        self.assertIn("Skipped 2 repeated station run(s)", out.getvalue())
