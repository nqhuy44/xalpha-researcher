import pytest
import pandas as pd
from src.data.sources.vnstock_client import VnstockClient
from src.config.settings import settings

# Skip the test if no API key is set in CI, though the user might be running locally with it.
@pytest.fixture
def client() -> VnstockClient:
    return VnstockClient()

def test_company_profile(client: VnstockClient):
    """Test fetching a company profile."""
    profile = client.get_company_profile("FPT")
    assert profile is not None, "Profile should not be None"
    assert isinstance(profile, dict), "Profile should be a dictionary"
    
def test_financial_report(client: VnstockClient):
    """Test fetching a financial report."""
    df = client.get_financial_report("FPT", period="quarter", report_type="BalanceSheet")
    assert df is not None, "DataFrame should not be None"
    assert isinstance(df, pd.DataFrame), "Result should be a pandas DataFrame"
    assert not df.empty, "DataFrame should not be empty"
    # Basic check to ensure it looks like a financial statement
    assert len(df.columns) > 0, "DataFrame should have columns"
