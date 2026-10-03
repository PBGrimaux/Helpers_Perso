"""Every metric shown in a table or tile must link to an explanation."""

import numpy as np
import pandas as pd

from core import forecast as fc
from core.metrics import METRIC_FORMATS
from ui import glossary

KPI_LABELS = [
    "Return p.a.", "Return (cumulative)", "Volatility", "Max drawdown", "Sharpe ratio",
    "Expected shortfall 1y", "Portfolio volatility", "Diversification ratio", "Effective nb of bets", "Avg. correlation",
    "Median final wealth", "Chance of reaching target", "Chance of ending below invested",
    "Chance of running out", "Median return p.a.",
    "Annualised turnover", "Total fees paid (% of start)", "Number of rebalances",
    "Rebalancing", "Management fee", "Transaction cost", "Inflation",
]


def test_all_table_metrics_have_an_entry():
    missing = [k for k in METRIC_FORMATS if glossary.url(k) is None]
    assert not missing, missing


def test_kpis_and_controls_have_an_entry():
    missing = [k for k in KPI_LABELS if glossary.help_text(k) is None]
    assert not missing, missing


def test_forecast_summary_keys_have_an_entry():
    cov = pd.DataFrame([[0.01]], index=["X"], columns=["X"])
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 1)
    res = fc.simulate(pd.Series({"X": 1.0}), pd.Series({"X": 0.03}), cov, 100.0, dates, n_paths=20)
    missing = [k for k in res.summary(target=150.0) if glossary.url(k) is None]
    assert not missing, missing


def test_anchors_unique_and_entries_complete():
    anchors = [s["anchor"] for s in glossary.SECTIONS] + [e["anchor"] for s in glossary.SECTIONS for e in s["entries"]]
    assert len(anchors) == len(set(anchors))
    for s in glossary.SECTIONS:
        for e in s["entries"]:
            assert e["meaning"] and e["computed"] and e["reading"], e["anchor"]
            assert glossary.url(e["anchor"]) == f"/methodology#{e['anchor']}"
    assert np.isfinite(len(glossary.short("Sharpe ratio")))
