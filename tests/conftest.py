"""Shared fixtures and configuration for pytest."""

from datetime import date
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_aws_session():
    """Create a mock AWS session."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_cost_explorer_client():
    """Create a mock Cost Explorer client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_organizations_client():
    """Create a mock Organizations client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_account_list():
    """Sample account list from AWS Organizations."""
    return [
        {"Id": "123456789012", "Name": "Production Account"},
        {"Id": "123456789013", "Name": "Development Account"},
        {"Id": "123456789014", "Name": "Test Account"},
        {"Id": "123456789015", "Name": "Shared Services Account"},
    ]


@pytest.fixture
def sample_cost_and_usage_response():
    """Sample Cost Explorer API response."""
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                "Groups": [
                    {
                        "Keys": ["123456789012"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "1000.50", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": ["123456789013"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "500.25", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": ["123456789014"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "250.75", "Unit": "USD"}
                        },
                    },
                ],
            },
            {
                "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                "Groups": [
                    {
                        "Keys": ["123456789012"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "1100.00", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": ["123456789013"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "550.50", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": ["123456789014"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "275.25", "Unit": "USD"}
                        },
                    },
                ],
            },
        ]
    }


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "account-groups": {
            "ss": {
                "123456789015": "Shared Services Account",
            },
            "production": {
                "123456789012": "Production Account",
            },
            "development": {
                "123456789013": "Development Account",
                "123456789014": "Test Account",
            },
        },
        "ss-allocations": {
            "production": 60,
            "development": 40,
        },
        "service-aggregations": {
            "compute": [
                "Amazon Elastic Compute Cloud - Compute",
                "AWS Lambda",
            ],
            "storage": [
                "Amazon Simple Storage Service",
            ],
        },
        "top-costs-count": {
            "account": 10,
            "service": 15,
        },
    }


@pytest.fixture
def sample_dates():
    """Sample date range for testing."""
    return {
        "start": date(2024, 1, 1),
        "end": date(2024, 3, 1),
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir
