"""
Unit tests for game station simulator functions in services.py.
One test class per station, testing the primary success path and the
integration behavior.
"""

from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase
from django.test.client import RequestFactory
import itertools
import json
import numpy as np
import pandas as pd
from pathlib import Path

from game.services import (
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
)
from game.models import StationRun
from game.helper_functions import get_visited_stations

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
        "Organism": ["Yeast", "Yeast", "E. coli", "Human"],
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


class TestVisitedStationsHelper(TestCase):
    def test_returns_empty_set_for_anonymous_user(self):
        visited = get_visited_stations(AnonymousUser())
        self.assertEqual(visited, set())

    def test_returns_unique_station_ids_for_user(self):
        user = get_user_model().objects.create_user(username="helper_user")
        StationRun.objects.create(player=user, station_id="sample_prep", params={}, score=0)
        StationRun.objects.create(player=user, station_id="mass_spec", params={}, score=0)
        StationRun.objects.create(player=user, station_id="mass_spec", params={}, score=0)

        visited = get_visited_stations(user)
        self.assertEqual(visited, {"sample_prep", "mass_spec"})


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
        StationRun.objects.create(player=user, station_id="sample_prep", params={}, score=0)
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
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "none"}
        )
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
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "zscore"}
        )
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
        result = _simulate_multiple_testing_corrector(df, {"correction_method": "magic"})
        self.assertFalse(result["success"])


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
        result = _simulate_statistical_analysis(pd.DataFrame(), {"statistical_test": "welch"})
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
        result = _simulate_statistical_analysis(df, {"statistical_test": "mannwhitneyu"})
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_unknown_test_fails(self, _mock_vp):
        result = _simulate_statistical_analysis(_make_dataset(), {"statistical_test": "magic"})
        self.assertFalse(result["success"])


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

    def test_score_is_zero_for_all_false_positives(self):
        with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
            # All Human → all false positives
            df = _make_dataset_with_stats()
            df[ORGANISM] = "Human"
            result = _simulate_final_report(df, {})
        self.assertEqual(result["score"], 0)


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
                result = _simulate_normalize(
                    _make_dataset(), {"normalization": method}
                )
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
        }
        for test_name in options:
            with self.subTest(statistical_test=test_name):
                result = _simulate_statistical_analysis(
                    _make_dataset(),
                    {"statistical_test": test_name},
                )
                self.assertEqual(result["success"], expected_success[test_name])


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
@patch("game.services.pd.read_csv", side_effect=_read_csv_for_spectral_search)
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

    def test_run_station_does_not_use_or_write_session_visited_stations(self):
        request = self._build_request()
        request.session["visited_stations"] = ["sample_prep"]

        def _runner(_dataset, _params):
            return {"success": True, "dataset": pd.DataFrame(), "score": 0, "feedback": "ok"}

        with patch.dict("game.services.STATION_SIMULATORS", {"mass_spec": _runner}):
            result = run_station(request, station_id="mass_spec", params={})

        self.assertTrue(result["success"])
        self.assertEqual(request.session["visited_stations"], ["sample_prep"])
        self.assertEqual(StationRun.objects.count(), 0)

    def test_run_station_success_without_visited_stations_session_key(self):
        request = self._build_request()

        def _runner(_dataset, _params):
            return {"success": True, "dataset": pd.DataFrame(), "score": 0, "feedback": "ok"}

        with patch.dict("game.services.STATION_SIMULATORS", {"sample_prep": _runner}):
            result = run_station(request, station_id="sample_prep", params={})

        self.assertTrue(result["success"])
        self.assertNotIn("visited_stations", request.session)
