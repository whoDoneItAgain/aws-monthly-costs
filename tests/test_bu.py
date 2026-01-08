"""Unit tests for amc.runmodes.bu module."""

from datetime import date


from amc.runmodes.bu.calculator import (
    _build_cost_matrix,
    _build_costs,
)
from amc.runmodes.bu import calculate_business_unit_costs


class TestBuildCosts:
    """Tests for _build_costs function."""

    def test_build_costs_basic(self):
        """Test building costs from API response."""
        response = {
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
                    ],
                }
            ]
        }

        result = _build_costs(response, daily_average=False)

        assert "2024-Jan" in result
        assert result["2024-Jan"]["123456789012"] == 1000.50
        assert result["2024-Jan"]["123456789013"] == 500.25

    def test_build_costs_daily_average(self):
        """Test building costs with daily average."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result = _build_costs(response, daily_average=True)

        # January 2024 has 31 days
        expected_daily = 3100.00 / 31
        assert abs(result["2024-Jan"]["123456789012"] - expected_daily) < 0.01

    def test_build_costs_leap_year_february(self):
        """Test building costs for February in a leap year (2024)."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "2900.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result = _build_costs(response, daily_average=True)

        # February 2024 has 29 days (leap year)
        expected_daily = 2900.00 / 29
        assert abs(result["2024-Feb"]["123456789012"] - expected_daily) < 0.01

    def test_build_costs_non_leap_year_february(self):
        """Test building costs for February in a non-leap year (2023)."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2023-02-01", "End": "2023-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "2800.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result = _build_costs(response, daily_average=True)

        # February 2023 has 28 days (non-leap year)
        expected_daily = 2800.00 / 28
        assert abs(result["2023-Feb"]["123456789012"] - expected_daily) < 0.01


class TestBuildCostMatrix:
    """Tests for _build_cost_matrix function."""

    def test_build_cost_matrix_without_shared_services(self):
        """Test building cost matrix without shared services allocation."""
        account_groups = {
            "ss": {"999999999999": "Shared Services"},
            "production": {"123456789012": "Prod Account"},
            "development": {"123456789013": "Dev Account"},
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 1000.00,
                "123456789013": 500.00,
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=None
        )

        assert result["2024-Jan"]["production"] == 1000.00
        assert result["2024-Jan"]["development"] == 500.00
        assert result["2024-Jan"]["ss"] == 0.00  # ss is included with 0 cost
        assert result["2024-Jan"]["total"] == 1500.00

    def test_build_cost_matrix_with_shared_services_not_allocated(self):
        """Test building cost matrix with shared services as separate line item."""
        account_groups = {
            "ss": {"999999999999": "Shared Services"},
            "production": {"123456789012": "Prod Account"},
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 1000.00,
            }
        }

        ss_costs = {
            "2024-Jan": {
                "ss": 200.00,
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=ss_costs
        )

        assert result["2024-Jan"]["production"] == 1000.00
        assert result["2024-Jan"]["ss"] == 200.00
        assert result["2024-Jan"]["total"] == 1200.00

    def test_build_cost_matrix_with_shared_services_allocated(self):
        """Test building cost matrix with shared services allocated to BUs."""
        account_groups = {
            "ss": {"999999999999": "Shared Services"},
            "production": {"123456789012": "Prod Account"},
            "development": {"123456789013": "Dev Account"},
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 1000.00,
                "123456789013": 500.00,
            }
        }

        ss_costs = {
            "2024-Jan": {
                "ss": 300.00,
            }
        }

        ss_percentages = {
            "production": 60,
            "development": 40,
        }

        result = _build_cost_matrix(
            account_groups,
            account_costs,
            ss_percentages=ss_percentages,
            ss_costs=ss_costs,
        )

        # Production: 1000 + (300 * 0.60) = 1180
        assert result["2024-Jan"]["production"] == 1180.00
        # Development: 500 + (300 * 0.40) = 620
        assert result["2024-Jan"]["development"] == 620.00
        assert (
            result["2024-Jan"]["ss"] == 0.00
        )  # ss is included with 0 cost when allocated
        assert result["2024-Jan"]["total"] == 1800.00

    def test_build_cost_matrix_zero_costs(self):
        """Test building cost matrix with zero costs."""
        account_groups = {
            "ss": {},
            "production": {"123456789012": "Prod Account"},
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 0.00,
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=None
        )

        assert result["2024-Jan"]["production"] == 0.00
        assert result["2024-Jan"]["total"] == 0.00

    def test_build_cost_matrix_missing_accounts(self):
        """Test building cost matrix with accounts not in cost data."""
        account_groups = {
            "ss": {},
            "production": {
                "123456789012": "Prod Account",
                "123456789014": "Missing Account",
            },
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 1000.00,
                # 123456789014 is missing
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=None
        )

        # Should sum available costs and treat missing as 0
        assert result["2024-Jan"]["production"] == 1000.00

    def test_build_cost_matrix_rounding(self):
        """Test proper rounding in cost matrix."""
        account_groups = {
            "ss": {},
            "production": {"123456789012": "Prod Account"},
        }

        account_costs = {
            "2024-Jan": {
                "123456789012": 99.999,
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=None
        )

        assert result["2024-Jan"]["production"] == 100.00

    def test_build_cost_matrix_with_unallocated_accounts(self):
        """Test building cost matrix with unallocated accounts."""
        account_groups = {
            "ss": {},
            "production": {"123456789012": "Prod Account"},
            "development": {"123456789013": "Dev Account"},
        }

        # Include accounts not in any BU
        account_costs = {
            "2024-Jan": {
                "123456789012": 1000.00,
                "123456789013": 500.00,
                "888888888888": 64.78,  # Unallocated account 1
                "777777777777": 100.00,  # Unallocated account 2
            }
        }

        result = _build_cost_matrix(
            account_groups, account_costs, ss_percentages=None, ss_costs=None
        )

        assert result["2024-Jan"]["production"] == 1000.00
        assert result["2024-Jan"]["development"] == 500.00
        assert result["2024-Jan"]["unallocated"] == 164.78
        assert result["2024-Jan"]["total"] == 1664.78


class TestCalculateBusinessUnitCosts:
    """Tests for calculate_business_unit_costs function."""

    def test_calculate_business_unit_costs_without_ss_allocation(
        self, mock_cost_explorer_client, sample_config
    ):
        """Test calculating BU costs without shared services allocation."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1000.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789013"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "500.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789014"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "300.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789015"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, all_account_costs = calculate_business_unit_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=None,
            daily_average=False,
        )

        assert "2024-Jan" in result
        assert result["2024-Jan"]["production"] == 1000.00
        assert result["2024-Jan"]["development"] == 800.00  # 500 + 300
        assert result["2024-Jan"]["ss"] == 200.00

        # Verify all_account_costs is returned
        assert all_account_costs is not None
        assert "2024-Jan" in all_account_costs

    def test_calculate_business_unit_costs_with_ss_allocation(
        self, mock_cost_explorer_client, sample_config
    ):
        """Test calculating BU costs with shared services allocation."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1000.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789013"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "500.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789014"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "300.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789015"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, _ = calculate_business_unit_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=sample_config["ss-allocations"],
            daily_average=False,
        )

        # Production: 1000 + (200 * 0.60) = 1120
        # Development: 800 + (200 * 0.40) = 880
        assert result["2024-Jan"]["production"] == 1120.00
        assert result["2024-Jan"]["development"] == 880.00
        assert (
            result["2024-Jan"]["ss"] == 0.00
        )  # ss is included with 0 cost when allocated

    def test_calculate_business_unit_costs_daily_average(
        self, mock_cost_explorer_client, sample_config
    ):
        """Test calculating BU costs with daily average."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, _ = calculate_business_unit_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=None,
            daily_average=True,
        )

        # 3100 / 31 days = 100
        assert abs(result["2024-Jan"]["production"] - 100.0) < 0.01

    def test_calculate_business_unit_costs_empty_response(
        self, mock_cost_explorer_client, sample_config
    ):
        """Test calculating BU costs with empty API response."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [],
                }
            ]
        }

        result, _ = calculate_business_unit_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=None,
            daily_average=False,
        )

        assert result["2024-Jan"]["production"] == 0.00
        assert result["2024-Jan"]["development"] == 0.00

    def test_calculate_business_unit_costs_single_api_call(
        self, mock_cost_explorer_client, sample_config
    ):
        """Test that only one API call is made (optimization verification)."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1000.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        calculate_business_unit_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=None,
            daily_average=False,
        )

        # Should only call get_cost_and_usage once (optimization)
        assert mock_cost_explorer_client.get_cost_and_usage.call_count == 1
