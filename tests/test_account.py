"""Unit tests for amc.runmodes.account module."""

from datetime import date


from amc.runmodes.account.calculator import (
    _build_cost_matrix,
    _build_costs,
)
from amc.runmodes.account import (
    calculate_account_costs,
    get_account_names,
)


class TestBuildCosts:
    """Tests for _build_costs function."""

    def test_build_costs_basic(
        self, sample_cost_and_usage_response, sample_account_list
    ):
        """Test building costs from API response."""
        result = _build_costs(
            sample_cost_and_usage_response, sample_account_list, daily_average=False
        )

        assert "2024-Jan" in result
        assert "2024-Feb" in result
        assert "Production Account" in result["2024-Jan"]
        assert result["2024-Jan"]["Production Account"] == 1000.50

    def test_build_costs_daily_average(
        self, sample_cost_and_usage_response, sample_account_list
    ):
        """Test building costs with daily average."""
        result = _build_costs(
            sample_cost_and_usage_response, sample_account_list, daily_average=True
        )

        # January has 31 days in 2024
        expected_daily = 1000.50 / 31
        assert "2024-Jan" in result
        assert abs(result["2024-Jan"]["Production Account"] - expected_daily) < 0.01

    def test_build_costs_leap_year_february(self, sample_account_list):
        """Test building costs for February in a leap year."""
        # 2024 is a leap year, February has 29 days
        leap_year_response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "2900.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        result = _build_costs(
            leap_year_response, sample_account_list, daily_average=True
        )

        # 2900 / 29 days = 100
        assert abs(result["2024-Feb"]["Production Account"] - 100.0) < 0.01

    def test_build_costs_non_leap_year_february(self, sample_account_list):
        """Test building costs for February in a non-leap year."""
        # 2023 is not a leap year, February has 28 days
        non_leap_response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2023-02-01", "End": "2023-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "2800.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        result = _build_costs(
            non_leap_response, sample_account_list, daily_average=True
        )

        # 2800 / 28 days = 100
        assert abs(result["2023-Feb"]["Production Account"] - 100.0) < 0.01

    def test_build_costs_missing_account(self, sample_account_list):
        """Test building costs with account not in account list."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["999999999999"],  # Account not in list
                            "Metrics": {
                                "UnblendedCost": {"Amount": "100.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        result = _build_costs(response, sample_account_list, daily_average=False)

        # Account not in list should not appear in results
        assert "2024-Jan" in result
        assert len(result["2024-Jan"]) == 0


class TestBuildCostMatrix:
    """Tests for _build_cost_matrix function."""

    def test_build_cost_matrix_basic(self):
        """Test building cost matrix from account costs."""
        account_costs = {
            "2024-Jan": {
                "Account A": 100.123,
                "Account B": 200.456,
            },
            "2024-Feb": {
                "Account A": 150.789,
                "Account B": 250.012,
            },
        }

        result = _build_cost_matrix(account_costs)

        assert "2024-Jan" in result
        assert "2024-Feb" in result
        assert result["2024-Jan"]["Account A"] == 100.12
        assert result["2024-Jan"]["Account B"] == 200.46
        assert result["2024-Jan"]["total"] == 300.58

    def test_build_cost_matrix_rounding(self):
        """Test proper rounding in cost matrix."""
        account_costs = {
            "2024-Jan": {
                "Account A": 99.995,  # Should round to 100.00
                "Account B": 0.004,  # Should round to 0.00
            },
        }

        result = _build_cost_matrix(account_costs)

        assert result["2024-Jan"]["Account A"] == 100.00
        assert result["2024-Jan"]["Account B"] == 0.00
        assert result["2024-Jan"]["total"] == 100.00

    def test_build_cost_matrix_empty(self):
        """Test building cost matrix with empty data."""
        account_costs = {
            "2024-Jan": {},
        }

        result = _build_cost_matrix(account_costs)

        assert result["2024-Jan"]["total"] == 0


class TestCalculateAccountCosts:
    """Tests for calculate_account_costs function."""

    def test_calculate_account_costs_basic(
        self,
        mock_cost_explorer_client,
        mock_organizations_client,
        sample_account_list,
        sample_cost_and_usage_response,
    ):
        """Test calculating account costs."""
        mock_organizations_client.list_accounts.return_value = {
            "Accounts": sample_account_list
        }
        mock_cost_explorer_client.get_cost_and_usage.return_value = (
            sample_cost_and_usage_response
        )

        result, _ = calculate_account_costs(
            mock_cost_explorer_client,
            mock_organizations_client,
            date(2024, 1, 1),
            date(2024, 3, 1),
            top_cost_count=5,
            daily_average=False,
        )

        assert "2024-Jan" in result
        assert "2024-Feb" in result
        assert "total" in result["2024-Jan"]
        assert "total" in result["2024-Feb"]

    def test_calculate_account_costs_pagination(
        self, mock_cost_explorer_client, mock_organizations_client
    ):
        """Test calculating account costs with paginated account list."""
        # First page
        first_page = [
            {"Id": "111111111111", "Name": "Account 1"},
            {"Id": "222222222222", "Name": "Account 2"},
        ]
        # Second page
        second_page = [
            {"Id": "333333333333", "Name": "Account 3"},
        ]

        mock_organizations_client.list_accounts.side_effect = [
            {"Accounts": first_page, "NextToken": "token123"},
            {"Accounts": second_page},
        ]

        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["111111111111"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "100.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["222222222222"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["333333333333"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "300.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, _ = calculate_account_costs(
            mock_cost_explorer_client,
            mock_organizations_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            top_cost_count=5,
            daily_average=False,
        )

        # Should have called list_accounts twice
        assert mock_organizations_client.list_accounts.call_count == 2
        assert "2024-Jan" in result

    def test_calculate_account_costs_top_accounts_only(
        self, mock_cost_explorer_client, mock_organizations_client
    ):
        """Test that only top N accounts are returned."""
        accounts = [{"Id": f"{i:012d}", "Name": f"Account {i}"} for i in range(1, 11)]

        mock_organizations_client.list_accounts.return_value = {"Accounts": accounts}

        # Create costs where Account 10 has highest cost
        groups = [
            {
                "Keys": [f"{i:012d}"],
                "Metrics": {"UnblendedCost": {"Amount": str(i * 100), "Unit": "USD"}},
            }
            for i in range(1, 11)
        ]

        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": groups,
                }
            ]
        }

        result, _ = calculate_account_costs(
            mock_cost_explorer_client,
            mock_organizations_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            top_cost_count=3,
            daily_average=False,
        )

        # Should only have 3 accounts + total
        assert len(result["2024-Jan"]) == 4  # 3 accounts + total


class TestGetAccountNames:
    """Tests for get_account_names function."""

    def test_get_account_names_basic(self):
        """Test extracting account names from cost matrix."""
        cost_matrix = {
            "Jan": {
                "Account A": 100,
                "Account B": 200,
                "total": 300,
            },
            "Feb": {
                "Account A": 150,
                "Account B": 250,
                "total": 400,
            },
        }

        result = get_account_names(cost_matrix)

        assert "Account A" in result
        assert "Account B" in result
        assert "total" in result

    def test_get_account_names_with_missing_accounts(self):
        """Test extracting account names when some months have different accounts."""
        cost_matrix = {
            "Jan": {
                "Account A": 100,
                "Account B": 200,
                "total": 300,
            },
            "Feb": {
                "Account A": 150,
                "Account C": 250,
                "total": 400,
            },
        }

        result = get_account_names(cost_matrix)

        # Should include all unique accounts
        assert "Account A" in result
        assert "Account B" in result
        assert "Account C" in result
        assert "total" in result

    def test_get_account_names_order(self):
        """Test that recent month's accounts come first."""
        cost_matrix = {
            "Jan": {
                "Account A": 100,
                "total": 100,
            },
            "Feb": {
                "Account B": 200,
                "Account C": 300,
                "total": 500,
            },
        }

        result = get_account_names(cost_matrix)

        # Feb is the last month, so its accounts should come first
        assert result.index("Account B") < result.index("Account A")
        assert result.index("Account C") < result.index("Account A")
