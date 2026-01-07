"""Additional unit tests for service calculator to achieve 100% coverage."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from amc.runmodes.service.calculator import _build_cost_matrix


class TestServiceCalculatorCoverage:
    """Tests for service calculator edge cases."""

    def test_build_cost_matrix_with_exclusions(self):
        """Test building cost matrix when services match exclusion list."""
        service_list = ["AWS Lambda", "Amazon S3", "AWS Support"]
        
        cost_matrix_raw = {
            "2024-01": {
                "AWS Lambda": 100.0,
                "Amazon S3": 200.0,
                "AWS Support": 50.0,  # This should be excluded
            },
            "2024-02": {
                "AWS Lambda": 150.0,
                "Amazon S3": 250.0,
                "AWS Support": 60.0,  # This should be excluded
            },
        }

        service_aggregations = {}
        # Support services are typically excluded
        exclusions = ["AWS Support"]

        result = _build_cost_matrix(
            service_list, cost_matrix_raw, service_aggregations, exclusions
        )

        # Check that AWS Support was excluded
        assert "AWS Support" not in result["2024-01"]
        assert "AWS Support" not in result["2024-02"]
        
        # Check that other services are included
        assert result["2024-01"]["AWS Lambda"] == 100.0
        assert result["2024-01"]["Amazon S3"] == 200.0
        assert result["2024-02"]["AWS Lambda"] == 150.0
        assert result["2024-02"]["Amazon S3"] == 250.0

    def test_build_cost_matrix_all_services_excluded(self):
        """Test building cost matrix when all services are excluded."""
        service_list = ["AWS Support", "AWS Tax"]
        
        cost_matrix_raw = {
            "2024-01": {
                "AWS Support": 50.0,
                "AWS Tax": 10.0,
            },
        }

        service_aggregations = {}
        exclusions = ["AWS Support", "AWS Tax"]

        result = _build_cost_matrix(
            service_list, cost_matrix_raw, service_aggregations, exclusions
        )

        # All services should be excluded, but a 'total' key is added
        # The function adds 'total' even when all services are excluded
        assert "AWS Support" not in result["2024-01"]
        assert "AWS Tax" not in result["2024-01"]
        assert result["2024-01"]["total"] == 0

    def test_build_cost_matrix_exclusion_not_in_service_list(self):
        """Test building cost matrix when exclusion doesn't match any service."""
        service_list = ["AWS Lambda", "Amazon S3"]
        
        cost_matrix_raw = {
            "2024-01": {
                "AWS Lambda": 100.0,
                "Amazon S3": 200.0,
            },
        }

        service_aggregations = {}
        # This service doesn't exist in the data
        exclusions = ["NonExistentService"]

        result = _build_cost_matrix(
            service_list, cost_matrix_raw, service_aggregations, exclusions
        )

        # All services should be included since exclusion doesn't match
        assert result["2024-01"]["AWS Lambda"] == 100.0
        assert result["2024-01"]["Amazon S3"] == 200.0

    def test_build_cost_matrix_with_aggregation_and_exclusion(self):
        """Test building cost matrix with both aggregation and exclusions."""
        service_list = ["Amazon EC2", "AWS Lambda", "AWS Support"]
        
        cost_matrix_raw = {
            "2024-01": {
                "Amazon EC2": 100.0,
                "AWS Lambda": 50.0,
                "AWS Support": 30.0,
            },
        }

        service_aggregations = {
            "Compute": ["Amazon EC2", "AWS Lambda"]
        }
        exclusions = ["AWS Support"]

        result = _build_cost_matrix(
            service_list, cost_matrix_raw, service_aggregations, exclusions
        )

        # Support should be excluded
        assert "AWS Support" not in result["2024-01"]
        
        # Compute aggregation should be created
        assert "Compute" in result["2024-01"]
        assert result["2024-01"]["Compute"] == 150.0
        
        # Individual services should not be in result (they're aggregated)
        assert "Amazon EC2" not in result["2024-01"]
        assert "AWS Lambda" not in result["2024-01"]
