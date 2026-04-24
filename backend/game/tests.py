"""
Unit tests for game station simulator functions in services.py.
One test class per station, testing the primary success path and the
prerequisite-station guard.
"""

from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
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
    _simulate_veit,
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
    _rank_products_pvalue,
)
from game.models import StationRun

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


# ---------------------------------------------------------------------------
# Station: sample_prep
# ---------------------------------------------------------------------------


class TestSamplePrepStation(TestCase):
    def test_always_succeeds(self):
        result = _simulate_sample_prep(None, {}, set())
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 0)
        self.assertIn("feedback", result)


# ---------------------------------------------------------------------------
# Station: mass_spec
# ---------------------------------------------------------------------------


class TestMassSpecStation(TestCase):
    def test_fails_without_sample_prep(self):
        result = _simulate_mass_spec(None, {}, set())
        self.assertFalse(result["success"])

    def test_success_after_sample_prep(self):
        result = _simulate_mass_spec(None, {}, {"sample_prep"})
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
    def test_fails_without_mass_spec_visited(self):
        # Guard condition: "mass_spec" must be in visited_stations
        result = _simulate_spectral_search(None, {}, set())
        self.assertFalse(result["success"])

    def test_raises_for_unknown_params(self):
        # No matching row in the parameter table → ValueError
        with patch("game.services.pd.read_csv", return_value=_make_param_table()):
            with self.assertRaises(ValueError):
                _simulate_spectral_search(
                    None,
                    {"tool": "unknown_tool"},
                    {"sample_prep", "mass_spec"},
                )

    @patch("game.services._create_histogram", return_value=_DUMMY_IMG)
    @patch("game.services.os.path.exists", return_value=True)
    def test_success_with_default_params(self, _mock_exists, _mock_hist):
        def _read_csv_side_effect(path, *args, **kwargs):
            if "ParameterTable" in str(path):
                return _make_param_table()
            return _make_dataset()

        with patch("game.services.pd.read_csv", side_effect=_read_csv_side_effect):
            result = _simulate_spectral_search(
                None, _DEFAULT_SPECTRAL_PARAMS, {"sample_prep", "mass_spec"}
            )

        self.assertTrue(result["success"])
        self.assertIn("num_prot", result)
        self.assertIsInstance(result["img"], list)


# ---------------------------------------------------------------------------
# Station: transform
# ---------------------------------------------------------------------------


class TestTransformStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_transform(
            _make_dataset(), {"transform_method": "log2"}, set()
        )
        self.assertFalse(result["success"])

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_log2_transformation(self, _mock_bp):
        df = _make_dataset()
        result = _simulate_transform(
            df, {"transform_method": "log2"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        self.assertAlmostEqual(
            result["dataset"][COND_A[0]].iloc[0], np.log2(10.0), places=5
        )

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_natural_log_transformation(self, _mock_bp):
        df = _make_dataset()
        result = _simulate_transform(
            df, {"transform_method": "ln"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        self.assertAlmostEqual(
            result["dataset"][COND_B[0]].iloc[0], np.log(20.0), places=5
        )

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_unknown_method_fails(self, _mock_bp):
        result = _simulate_transform(
            _make_dataset(), {"transform_method": "sqrt"}, {"spectral_search"}
        )
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Station: filtering
# ---------------------------------------------------------------------------


class TestFilteringStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_filtering(_make_dataset(), {}, set())
        self.assertFalse(result["success"])

    def test_fails_on_empty_dataset(self):
        result = _simulate_filtering(pd.DataFrame(), {}, {"spectral_search"})
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
            {"spectral_search"},
        )
        self.assertTrue(result["success"])
        self.assertIn("num_pro", result)


# ---------------------------------------------------------------------------
# Station: normalize
# ---------------------------------------------------------------------------


class TestNormalizeStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "median"}, set()
        )
        self.assertFalse(result["success"])

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_no_normalization(self, _mock_hc):
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "none"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_median_normalization(self, _mock_hc):
        df = _make_dataset()
        result = _simulate_normalize(
            df, {"normalization": "median"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        # After median normalization each column should be centered near zero
        col = COND_A[0]
        self.assertAlmostEqual(result["dataset"][col].median(), 0.0, places=5)

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_zscore_normalization(self, _mock_hc):
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "zscore"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])

    @patch("game.services.histogram_compare", return_value=[_DUMMY_IMG])
    def test_unknown_method_fails(self, _mock_hc):
        result = _simulate_normalize(
            _make_dataset(), {"normalization": "magic"}, {"spectral_search"}
        )
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Station: imputer
# ---------------------------------------------------------------------------


class TestImputer(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_imputer(_make_dataset(), {}, set())
        self.assertFalse(result["success"])

    def test_fails_on_empty_dataset(self):
        result = _simulate_imputer(pd.DataFrame(), {}, {"spectral_search"})
        self.assertFalse(result["success"])

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_no_imputation(self, _mock_plot):
        df = _make_dataset()
        result = _simulate_imputer(
            df, {"imputation_method": "none"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        # Values must remain unchanged
        pd.testing.assert_frame_equal(
            result["dataset"][COND_A + COND_B], df[COND_A + COND_B]
        )

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_mean_imputation_fills_nans(self, _mock_plot):
        df = _make_dataset()
        df.loc[0, COND_A[0]] = np.nan  # introduce one missing value
        result = _simulate_imputer(
            df, {"imputation_method": "mean"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["dataset"][COND_A[0]].isna().any())

    @patch("game.services.imputer_before_after_stripgrid", return_value=_DUMMY_IMG)
    def test_minprob_imputation(self, _mock_plot):
        df = _make_dataset()
        df.loc[0, COND_B[1]] = np.nan
        result = _simulate_imputer(
            df, {"imputation_method": "minprob"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["dataset"][COND_B[1]].isna().any())


# ---------------------------------------------------------------------------
# Station: multiple_testing_corrector
# ---------------------------------------------------------------------------


class TestMultipleTestingCorrectorStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_multiple_testing_corrector(_make_dataset(), {}, set())
        self.assertFalse(result["success"])

    def test_fails_without_pvalue_column(self):
        result = _simulate_multiple_testing_corrector(
            _make_dataset(), {}, {"spectral_search"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_benjamini_hochberg_correction(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(
            df, {"correction_method": "bh"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 10)
        # Adjusted p-values should remain in [0, 1]
        self.assertTrue((result["dataset"][PVALUE] <= 1.0).all())

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_bonferroni_correction(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(
            df, {"correction_method": "bonferroni"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 6)

    @patch("game.services.mtc_histograms", return_value=[_DUMMY_IMG])
    def test_unknown_correction_fails(self, _mock_hist):
        df = _make_dataset_with_stats()
        result = _simulate_multiple_testing_corrector(
            df, {"correction_method": "magic"}, {"spectral_search"}
        )
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Station: the_cutter
# ---------------------------------------------------------------------------


class TestTheCutterStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_the_cutter(_make_dataset(), {}, set())
        self.assertFalse(result["success"])

    def test_fails_without_fc_column(self):
        result = _simulate_the_cutter(_make_dataset(), {}, {"spectral_search"})
        self.assertFalse(result["success"])

    @patch("game.services.plot_significant_proteins", return_value=_DUMMY_IMG)
    def test_cutoff_filters_correctly(self, _mock_plot):
        df = _make_dataset_with_stats()
        # FC cutoff 1.0, p-value cutoff 0.05 → keeps rows with |FC|>=1 and p<=0.05
        result = _simulate_the_cutter(
            df,
            {"fold_change_cutoff": 1.0, "pvalue_cutoff": 0.05},
            {"spectral_search"},
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
            {"spectral_search"},
        )
        self.assertEqual(len(result["dataset"]), 0)


# ---------------------------------------------------------------------------
# Station: statistical_analysis
# ---------------------------------------------------------------------------


class TestStatisticalAnalysisStation(TestCase):
    def test_fails_without_spectral_search(self):
        result = _simulate_statistical_analysis(
            _make_dataset(), {"statistical_test": "welch"}, set()
        )
        self.assertFalse(result["success"])

    def test_fails_on_empty_dataset(self):
        result = _simulate_statistical_analysis(
            pd.DataFrame(), {"statistical_test": "welch"}, {"spectral_search"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_welch_ttest_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(
            df, {"statistical_test": "welch"}, {"spectral_search"}
        )
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
            df, {"statistical_test": "mannwhitneyu"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_limma_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(
            df, {"statistical_test": "limma"}, {"spectral_search"}
        )
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
        result = _simulate_statistical_analysis(
            base_df, {"statistical_test": "limma"}, {"spectral_search"}
        )
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
            _make_dataset(), {"statistical_test": "magic"}, {"spectral_search"}
        )
        self.assertFalse(result["success"])

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_rank_products_produces_pvalues(self, _mock_vp):
        df = _make_dataset()
        result = _simulate_statistical_analysis(
            df, {"statistical_test": "rank_products"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        self.assertIn(PVALUE, result["dataset"].columns)
        self.assertIn(FC, result["dataset"].columns)
        pvals = result["dataset"][PVALUE].dropna()
        self.assertTrue((pvals >= 0).all() and (pvals <= 1).all())

    @patch("game.services.volcano_plot", return_value=_DUMMY_IMG)
    def test_rank_products_includes_proteins_with_missing_values(self, _mock_vp):
        """A protein with NaN in some replicates but ≥1 valid value per condition
        should still receive a p-value from the rank products test."""
        df = _make_dataset()
        # Protein 0: keep only replicate 0 in each condition; wipe the rest
        df.loc[0, COND_A[1]] = np.nan
        df.loc[0, COND_A[2]] = np.nan
        df.loc[0, COND_B[1]] = np.nan
        df.loc[0, COND_B[2]] = np.nan
        result = _simulate_statistical_analysis(
            df, {"statistical_test": "rank_products"}, {"spectral_search"}
        )
        self.assertTrue(result["success"])
        p0 = result["dataset"].loc[0, PVALUE]
        self.assertTrue(
            np.isfinite(p0),
            f"Expected finite p-value for NaN-heavy protein, got {p0}",
        )


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


class TestRankProductsPvalue(TestCase):
    """Unit tests for the _rank_products_pvalue analytic helper."""

    def test_returns_valid_p_value(self):
        """A typical rank product should yield a p-value in [0, 1]."""
        p = _rank_products_pvalue(0.01, n=100, k=6)
        self.assertTrue(0.0 <= p <= 1.0)

    def test_very_small_rp_gives_small_pvalue(self):
        """A rank product near zero (top-ranked in every replicate) should be highly significant."""
        p = _rank_products_pvalue(1e-10, n=500, k=6)
        self.assertLess(p, 0.01)

    def test_rp_near_one_gives_large_pvalue(self):
        """A rank product near 1 (bottom-ranked in every replicate) should not be significant."""
        p = _rank_products_pvalue(0.99**6, n=500, k=6)
        self.assertGreater(p, 0.05)

    def test_invalid_inputs_return_nan(self):
        """Non-positive or non-finite inputs should return NaN."""
        self.assertTrue(np.isnan(_rank_products_pvalue(0.0, n=100, k=6)))
        self.assertTrue(np.isnan(_rank_products_pvalue(-0.5, n=100, k=6)))
        self.assertTrue(np.isnan(_rank_products_pvalue(np.nan, n=100, k=6)))
        self.assertTrue(np.isnan(_rank_products_pvalue(0.5, n=0, k=6)))
        self.assertTrue(np.isnan(_rank_products_pvalue(0.5, n=100, k=0)))
# ---------------------------------------------------------------------------


class TestVeitStation(TestCase):
    def test_fails_on_empty_dataset(self):
        result = _simulate_veit(pd.DataFrame(), {}, set())
        self.assertFalse(result["success"])

    def test_counts_true_and_false_positives(self):
        with patch("game.services.plot_scores", return_value=_DUMMY_IMG):
            df = _make_dataset_with_stats()
            # Yeast P0001 has FC=-1.5 → true positive; E.coli P0003 has FC=1.8 → true positive
            # Yeast P0002 has FC=-0.3 → true positive (FC < 0); Human P0004 → false positive
            result = _simulate_veit(df, {}, set())
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
            result = _simulate_veit(df, {}, set())
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
    @patch("game.services.os.path.exists", return_value=True)
    def test_spectral_search_parameter_configurations(self, _mock_exists, _mock_hist):
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
                        {"sample_prep", "mass_spec"},
                    )
                    self.assertTrue(result["success"])
                    self.assertIsInstance(result["dataset"], pd.DataFrame)

    @patch("game.services.tr_boxplot", return_value=_DUMMY_IMG)
    def test_transform_parameter_configurations(self, _mock_bp):
        options = self.station_options["transform"]["parameters"][0]["options"]
        for method in options:
            with self.subTest(transform_method=method):
                result = _simulate_transform(
                    _make_dataset(), {"transform_method": method}, {"spectral_search"}
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
                    {"spectral_search"},
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
                    _make_dataset(), {"normalization": method}, {"spectral_search"}
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
                    {"spectral_search"},
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
                    {"spectral_search"},
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
                    {"spectral_search"},
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
            "rank_products": True,
        }
        for test_name in options:
            with self.subTest(statistical_test=test_name):
                result = _simulate_statistical_analysis(
                    _make_dataset(),
                    {"statistical_test": test_name},
                    {"spectral_search"},
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
@patch("game.services.os.path.exists", return_value=True)
@patch("game.services.pd.read_csv", side_effect=_read_csv_for_spectral_search)
class TestFullWorkflow(TestCase):
    """
    Chains every station in the canonical pipeline order and verifies that data
    flows correctly from one station to the next, ending with a scored veit result.

    Station order:
      sample_prep → mass_spec → spectral_search → transform → filtering →
      normalize → imputer → statistical_analysis → multiple_testing_corrector →
      the_cutter → veit
    """

    def test_full_pipeline(
        self,
        _mock_csv,
        _mock_exists,
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
        visited: set[str] = set()
        dataset = None

        # --- 1. sample_prep ---
        r = _simulate_sample_prep(dataset, {}, visited)
        self.assertTrue(r["success"], "sample_prep failed")
        dataset = r["dataset"]
        visited.add("sample_prep")

        # --- 2. mass_spec ---
        r = _simulate_mass_spec(dataset, {}, visited)
        self.assertTrue(r["success"], "mass_spec failed")
        dataset = r["dataset"]
        visited.add("mass_spec")

        # --- 3. spectral_search ---
        r = _simulate_spectral_search(dataset, _DEFAULT_SPECTRAL_PARAMS, visited)
        self.assertTrue(r["success"], "spectral_search failed")
        self.assertIsInstance(r["dataset"], pd.DataFrame)
        self.assertFalse(r["dataset"].empty)
        dataset = r["dataset"]
        visited.add("spectral_search")

        # --- 4. transform (log2) ---
        r = _simulate_transform(dataset, {"transform_method": "log2"}, visited)
        self.assertTrue(r["success"], "transform failed")
        dataset = r["dataset"]
        visited.add("transform")

        # --- 5. filtering ---
        r = _simulate_filtering(
            dataset,
            {"remove_missing_proteins": 6, "min_peptides_per_protein": 1},
            visited,
        )
        self.assertTrue(r["success"], "filtering failed")
        self.assertIsNotNone(r["dataset"])
        self.assertFalse(r["dataset"].empty)
        dataset = r["dataset"]
        visited.add("filtering")

        # --- 6. normalize (median) ---
        r = _simulate_normalize(dataset, {"normalization": "median"}, visited)
        self.assertTrue(r["success"], "normalize failed")
        dataset = r["dataset"]
        visited.add("normalize")

        # --- 7. imputer (mean) ---
        r = _simulate_imputer(dataset, {"imputation_method": "mean"}, visited)
        self.assertTrue(r["success"], "imputer failed")
        dataset = r["dataset"]
        visited.add("imputer")

        # --- 8. statistical_analysis (welch) ---
        r = _simulate_statistical_analysis(
            dataset, {"statistical_test": "welch"}, visited
        )
        self.assertTrue(r["success"], "statistical_analysis failed")
        self.assertIn(PVALUE, r["dataset"].columns)
        self.assertIn(FC, r["dataset"].columns)
        dataset = r["dataset"]
        visited.add("statistical_analysis")

        # --- 9. multiple_testing_corrector (BH) ---
        r = _simulate_multiple_testing_corrector(
            dataset, {"correction_method": "bh"}, visited
        )
        self.assertTrue(r["success"], "multiple_testing_corrector failed")
        dataset = r["dataset"]
        visited.add("multiple_testing_corrector")

        # --- 10. the_cutter ---
        r = _simulate_the_cutter(
            dataset,
            {"fold_change_cutoff": 0.0, "pvalue_cutoff": 1.0},  # permissive: keep all
            visited,
        )
        self.assertIsNotNone(r["dataset"])
        dataset = r["dataset"]
        visited.add("the_cutter")

        # --- 11. veit (final scoring) ---
        r = _simulate_veit(dataset, {}, visited)
        self.assertTrue(r["success"], "veit failed")
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

    def test_run_station_tracks_visited_stations_in_session(self):
        request = self._build_request()
        request.session["visited_stations"] = ["sample_prep"]

        seen_visited = {}

        def _runner(_dataset, _params, visited_stations):
            seen_visited["value"] = set(visited_stations)
            return {"success": True, "dataset": pd.DataFrame(), "score": 0, "feedback": "ok"}

        with patch.dict("game.services.STATION_SIMULATORS", {"mass_spec": _runner}):
            result = run_station(request, station_id="mass_spec", params={})

        self.assertTrue(result["success"])
        self.assertEqual(seen_visited["value"], {"sample_prep"})
        self.assertCountEqual(request.session["visited_stations"], ["mass_spec", "sample_prep"])
        self.assertEqual(StationRun.objects.count(), 0)

    def test_run_station_does_not_duplicate_session_visited_station(self):
        request = self._build_request()
        request.session["visited_stations"] = ["sample_prep"]

        def _runner(_dataset, _params, _visited_stations):
            return {"success": True, "dataset": pd.DataFrame(), "score": 0, "feedback": "ok"}

        with patch.dict("game.services.STATION_SIMULATORS", {"sample_prep": _runner}):
            result = run_station(request, station_id="sample_prep", params={})

        self.assertTrue(result["success"])
        self.assertEqual(request.session["visited_stations"], ["sample_prep"])
