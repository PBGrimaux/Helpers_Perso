import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def weekly_dates():
    return pd.date_range("2015-01-02", periods=520, freq="W-FRI")


def constant_growth(dates, annual_rate, start=100.0):
    """Prices growing at a constant weekly rate."""
    g = (1 + annual_rate) ** (1 / 52)
    return pd.Series(start * g ** np.arange(len(dates)), index=dates)
