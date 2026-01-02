"""Unit tests for amc.runmodes.service module."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from amc.runmodes.service import (
    _build_cost_matrix,
    _build_costs,
    calculate_service_costs,
    get_service_list,
)


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
                            "Keys": ["Amazon EC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "1000.50", "Unit": "USD"}},
                        },
                        {
                            "Keys": ["Amazon S3"],
                            "Metrics": {"UnblendedCost": {"Amount": "500.25", "Unit": "USD"}},
                        },
                    ],
                }
            ]
        }
        
        costs, services = _build_costs(response, daily_average=False)
        
        assert "Jan" in costs
        assert costs["Jan"]["Amazon EC2"] == 1000.50
        assert costs["Jan"]["Amazon S3"] == 500.25
        assert "Amazon EC2" in services
        assert "Amazon S3" in services

    def test_build_costs_daily_average(self):
        """Test building costs with daily average."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}},
                        },
                    ],
                }
            ]
        }
        
        costs, services = _build_costs(response, daily_average=True)
        
        # January 2024 has 31 days
        expected_daily = 3100.00 / 31
        assert abs(costs["Jan"]["Amazon EC2"] - expected_daily) < 0.01

    def test_build_costs_leap_year_february(self):
        """Test building costs for February in a leap year."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "2900.00", "Unit": "USD"}},
                        },
                    ],
                }
            ]
        }
        
        costs, services = _build_costs(response, daily_average=True)
        
        # February 2024 has 29 days (leap year)
        expected_daily = 2900.00 / 29
        assert abs(costs["Feb"]["Amazon EC2"] - expected_daily) < 0.01

    def test_build_costs_non_leap_year_february(self):
        """Test building costs for February in a non-leap year."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2023-02-01", "End": "2023-03-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "2800.00", "Unit": "USD"}},
                        },
                    ],
                }
            ]
        }
        
        costs, services = _build_costs(response, daily_average=True)
        
        # February 2023 has 28 days (non-leap year)
        expected_daily = 2800.00 / 28
        assert abs(costs["Feb"]["Amazon EC2"] - expected_daily) < 0.01

    def test_build_costs_unique_services(self):
        """Test that service list contains unique services."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "100.00", "Unit": "USD"}}},
                        {"Keys": ["Amazon S3"], "Metrics": {"UnblendedCost": {"Amount": "200.00", "Unit": "USD"}}},
                    ],
                },
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "150.00", "Unit": "USD"}}},
                        {"Keys": ["AWS Lambda"], "Metrics": {"UnblendedCost": {"Amount": "50.00", "Unit": "USD"}}},
                    ],
                },
            ]
        }
        
        costs, services = _build_costs(response, daily_average=False)
        
        # Should have unique services
        assert len(services) == 3
        assert "Amazon EC2" in services
        assert "Amazon S3" in services
        assert "AWS Lambda" in services


class TestBuildCostMatrix:
    """Tests for _build_cost_matrix function."""

    def test_build_cost_matrix_without_aggregation(self):
        """Test building cost matrix without service aggregation."""
        service_list = ["Amazon EC2", "Amazon S3"]
        service_costs = {
            "Jan": {
                "Amazon EC2": 1000.00,
                "Amazon S3": 500.00,
            }
        }
        service_aggregation = {}
        
        result = _build_cost_matrix(service_list, service_costs, service_aggregation)
        
        assert result["Jan"]["Amazon EC2"] == 1000.00
        assert result["Jan"]["Amazon S3"] == 500.00
        assert result["Jan"]["total"] == 1500.00

    def test_build_cost_matrix_with_aggregation(self, sample_config):
        """Test building cost matrix with service aggregation."""
        service_list = [
            "Amazon Elastic Compute Cloud - Compute",
            "AWS Lambda",
            "Amazon Simple Storage Service",
        ]
        service_costs = {
            "Jan": {
                "Amazon Elastic Compute Cloud - Compute": 800.00,
                "AWS Lambda": 200.00,
                "Amazon Simple Storage Service": 500.00,
            }
        }
        
        result = _build_cost_matrix(
            service_list,
            service_costs,
            sample_config["service-aggregations"]
        )
        
        # Compute aggregation: EC2 + Lambda = 1000
        assert result["Jan"]["compute"] == 1000.00
        # Storage aggregation: S3 = 500
        assert result["Jan"]["storage"] == 500.00
        assert result["Jan"]["total"] == 1500.00
        # Individual services should not appear
        assert "Amazon Elastic Compute Cloud - Compute" not in result["Jan"]
        assert "AWS Lambda" not in result["Jan"]

    def test_build_cost_matrix_mixed_aggregation(self):
        """Test building cost matrix with some aggregated and some non-aggregated services."""
        service_list = ["Amazon EC2", "Amazon S3", "Amazon RDS"]
        service_costs = {
            "Jan": {
                "Amazon EC2": 800.00,
                "Amazon S3": 200.00,
                "Amazon RDS": 500.00,
            }
        }
        service_aggregation = {
            "compute": ["Amazon EC2"],
        }
        
        result = _build_cost_matrix(service_list, service_costs, service_aggregation)
        
        # EC2 is aggregated
        assert result["Jan"]["compute"] == 800.00
        # S3 and RDS are not aggregated
        assert result["Jan"]["Amazon S3"] == 200.00
        assert result["Jan"]["Amazon RDS"] == 500.00
        assert result["Jan"]["total"] == 1500.00

    def test_build_cost_matrix_zero_costs(self):
        """Test building cost matrix with zero costs."""
        service_list = ["Amazon EC2"]
        service_costs = {
            "Jan": {
                "Amazon EC2": 0.00,
            }
        }
        
        result = _build_cost_matrix(service_list, service_costs, {})
        
        assert result["Jan"]["Amazon EC2"] == 0.00
        assert result["Jan"]["total"] == 0.00

    def test_build_cost_matrix_rounding(self):
        """Test proper rounding in cost matrix."""
        service_list = ["Amazon EC2"]
        service_costs = {
            "Jan": {
                "Amazon EC2": 99.999,
            }
        }
        
        result = _build_cost_matrix(service_list, service_costs, {})
        
        assert result["Jan"]["Amazon EC2"] == 100.00


class TestCalculateServiceCosts:
    """Tests for calculate_service_costs function."""

    def test_calculate_service_costs_basic(self, mock_cost_explorer_client):
        """Test calculating service costs."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "1000.00", "Unit": "USD"}}},
                        {"Keys": ["Amazon S3"], "Metrics": {"UnblendedCost": {"Amount": "500.00", "Unit": "USD"}}},
                        {"Keys": ["AWS Lambda"], "Metrics": {"UnblendedCost": {"Amount": "100.00", "Unit": "USD"}}},
                    ],
                }
            ]
        }
        
        result = calculate_service_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            service_aggregations={},
            top_cost_count=5,
            daily_average=False,
        )
        
        assert "Jan" in result
        assert "total" in result["Jan"]

    def test_calculate_service_costs_with_aggregation(self, mock_cost_explorer_client, sample_config):
        """Test calculating service costs with aggregation."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {"Keys": ["Amazon Elastic Compute Cloud - Compute"], "Metrics": {"UnblendedCost": {"Amount": "800.00", "Unit": "USD"}}},
                        {"Keys": ["AWS Lambda"], "Metrics": {"UnblendedCost": {"Amount": "200.00", "Unit": "USD"}}},
                        {"Keys": ["Amazon Simple Storage Service"], "Metrics": {"UnblendedCost": {"Amount": "500.00", "Unit": "USD"}}},
                    ],
                }
            ]
        }
        
        result = calculate_service_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            service_aggregations=sample_config["service-aggregations"],
            top_cost_count=5,
            daily_average=False,
        )
        
        # Should have aggregated services
        assert "compute" in result["Jan"]
        assert "storage" in result["Jan"]

    def test_calculate_service_costs_top_services_only(self, mock_cost_explorer_client):
        """Test that only top N services are returned."""
        groups = [
            {"Keys": [f"Service {i}"], "Metrics": {"UnblendedCost": {"Amount": str(i * 100), "Unit": "USD"}}}
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
        
        result = calculate_service_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            service_aggregations={},
            top_cost_count=3,
            daily_average=False,
        )
        
        # Should only have 3 services + total
        assert len(result["Jan"]) == 4

    def test_calculate_service_costs_daily_average(self, mock_cost_explorer_client):
        """Test calculating service costs with daily average."""
        mock_cost_explorer_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}}},
                    ],
                }
            ]
        }
        
        result = calculate_service_costs(
            mock_cost_explorer_client,
            date(2024, 1, 1),
            date(2024, 2, 1),
            service_aggregations={},
            top_cost_count=5,
            daily_average=True,
        )
        
        # 3100 / 31 days = 100
        assert abs(result["Jan"]["Amazon EC2"] - 100.0) < 0.01


class TestGetServiceList:
    """Tests for get_service_list function."""

    def test_get_service_list_basic(self):
        """Test extracting service list from cost matrix."""
        cost_matrix = {
            "Jan": {
                "Amazon EC2": 100,
                "Amazon S3": 200,
                "total": 300,
            },
            "Feb": {
                "Amazon EC2": 150,
                "Amazon S3": 250,
                "total": 400,
            },
        }
        
        result = get_service_list(cost_matrix)
        
        assert "Amazon EC2" in result
        assert "Amazon S3" in result
        assert "total" in result

    def test_get_service_list_with_missing_services(self):
        """Test extracting service list when some months have different services."""
        cost_matrix = {
            "Jan": {
                "Amazon EC2": 100,
                "Amazon S3": 200,
                "total": 300,
            },
            "Feb": {
                "Amazon EC2": 150,
                "AWS Lambda": 250,
                "total": 400,
            },
        }
        
        result = get_service_list(cost_matrix)
        
        # Should include all unique services
        assert "Amazon EC2" in result
        assert "Amazon S3" in result
        assert "AWS Lambda" in result
        assert "total" in result

    def test_get_service_list_order(self):
        """Test that recent month's services come first."""
        cost_matrix = {
            "Jan": {
                "Amazon EC2": 100,
                "total": 100,
            },
            "Feb": {
                "Amazon S3": 200,
                "AWS Lambda": 300,
                "total": 500,
            },
        }
        
        result = get_service_list(cost_matrix)
        
        # Feb is the last month, so its services should come first
        assert result.index("Amazon S3") < result.index("Amazon EC2")
        assert result.index("AWS Lambda") < result.index("Amazon EC2")

    def test_get_service_list_with_aggregations(self):
        """Test extracting service list with aggregations (reserved for future use)."""
        cost_matrix = {
            "Jan": {
                "compute": 1000,
                "storage": 500,
                "total": 1500,
            },
        }
        
        result = get_service_list(cost_matrix, service_aggregations={})
        
        assert "compute" in result
        assert "storage" in result
        assert "total" in result
