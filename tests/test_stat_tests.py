import pytest

from metrics.stat_tests import bootstrap_mean_ci, paired_comparison, paired_pnl_changes


def test_paired_pnl_changes_aligns_equity_curves():
    differences = paired_pnl_changes([0, 2, 3, 6], [0, 1, 3, 4])

    assert differences == [1, -1, 2]


def test_paired_comparison_reports_direction_and_ci():
    comparison = paired_comparison("a", [0, 2, 4, 6, 8], "b", [0, 1, 2, 3, 4], bootstrap_samples=50)

    assert comparison.mean_difference == pytest.approx(1.0)
    assert comparison.t_stat == 0.0
    assert comparison.probability_left_better == 1.0
    assert comparison.observations == 4


def test_bootstrap_ci_handles_empty_values():
    assert bootstrap_mean_ci([]) == (0.0, 0.0)
