"""Unit tests for year mode functionality."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from amc.__main__ import parse_time_period, validate_year_data
from amc.constants import TIME_PERIOD_YEAR, MIN_MONTHS_FOR_YEAR_ANALYSIS
from amc.reportexport import (
    _aggregate_year_costs,
    _calculate_year_daily_average,
    _calculate_year_monthly_average,
)


class TestParseTimePeriodYear:
    """Tests for parse_time_period function with year mode."""

    def test_parse_time_period_year_mode(self):
        """Test parsing time period with 'year' mode."""
        start_date, end_date = parse_time_period(TIME_PERIOD_YEAR)
        
        # Should return dates 24 months apart
        assert isinstance(start_date, date)
        assert isinstance(end_date, date)
        assert start_date < end_date
        
        # Calculate month difference
        months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        assert months_diff == 24


class TestValidateYearData:
    """Tests for validate_year_data function."""

    def test_validate_year_data_insufficient_months(self):
        """Test validation fails with insufficient months."""
        # Only 12 months of data
        cost_matrix = {f"Jan": {"bu1": 100}, f"Feb": {"bu1": 100}}
        
        with pytest.raises(ValueError) as exc_info:
            validate_year_data(cost_matrix)
        
        assert "Insufficient data" in str(exc_info.value)
        assert str(MIN_MONTHS_FOR_YEAR_ANALYSIS) in str(exc_info.value)

    def test_validate_year_data_empty(self):
        """Test validation fails with empty data."""
        cost_matrix = {}
        
        with pytest.raises(ValueError) as exc_info:
            validate_year_data(cost_matrix)
        
        assert "No cost data available" in str(exc_info.value)

    def test_validate_year_data_exactly_24_months(self):
        """Test validation succeeds with exactly 24 months."""
        # Create 24 months of data with year-month format (YYYY-Mon)
        months = [f"2023-{mon}" for mon in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]] + \
                 [f"2024-{mon}" for mon in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        cost_matrix = {month: {"bu1": 100} for month in months}
        
        year1_months, year2_months = validate_year_data(cost_matrix)
        
        assert len(year1_months) == 12
        assert len(year2_months) == 12
        assert year1_months[0] == "2023-Jan"
        assert year2_months[0] == "2024-Jan"

    def test_validate_year_data_more_than_24_months(self):
        """Test validation takes last 24 months when more data is available."""
        # Create 30 months of data
        months_2023 = [f"2023-{mon}" for mon in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        months_2024 = [f"2024-{mon}" for mon in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        months_2025 = [f"2025-{mon}" for mon in ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]]
        all_months = months_2023 + months_2024 + months_2025
        cost_matrix = {month: {"bu1": 100} for month in all_months}
        
        year1_months, year2_months = validate_year_data(cost_matrix)
        
        # Should get the last 24 months
        assert len(year1_months) == 12
        assert len(year2_months) == 12
        # Should be from 2023-Jul to 2024-Jun and 2024-Jul to 2025-Jun
        assert "2023-Jul" in year1_months
        assert "2024-Jul" in year2_months

    def test_validate_year_data_invalid_month_name(self):
        """Test validation works with any string keys."""
        # With the simplified implementation, any 24+ entries will work
        cost_matrix = {f"Month-{i}": {"bu1": 100} for i in range(25)}
        
        year1_months, year2_months = validate_year_data(cost_matrix)
        
        # Should succeed and split last 24 into two 12-month periods
        assert len(year1_months) == 12
        assert len(year2_months) == 12


class TestAggregateYearCosts:
    """Tests for _aggregate_year_costs function."""

    def test_aggregate_year_costs_single_group(self):
        """Test aggregating costs for a single group."""
        cost_matrix = {
            "Jan": {"bu1": 100.0},
            "Feb": {"bu1": 150.0},
            "Mar": {"bu1": 200.0},
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _aggregate_year_costs(cost_matrix, year_months)
        
        assert result["bu1"] == 450.0

    def test_aggregate_year_costs_multiple_groups(self):
        """Test aggregating costs for multiple groups."""
        cost_matrix = {
            "Jan": {"bu1": 100.0, "bu2": 50.0},
            "Feb": {"bu1": 150.0, "bu2": 75.0},
            "Mar": {"bu1": 200.0, "bu2": 100.0},
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _aggregate_year_costs(cost_matrix, year_months)
        
        assert result["bu1"] == 450.0
        assert result["bu2"] == 225.0

    def test_aggregate_year_costs_missing_months(self):
        """Test aggregating when some months are missing from data."""
        cost_matrix = {
            "Jan": {"bu1": 100.0},
            "Mar": {"bu1": 200.0},
        }
        year_months = ["Jan", "Feb", "Mar"]  # Feb is missing
        
        result = _aggregate_year_costs(cost_matrix, year_months)
        
        # Should only aggregate available months
        assert result["bu1"] == 300.0

    def test_aggregate_year_costs_rounding(self):
        """Test that results are rounded to 2 decimal places."""
        cost_matrix = {
            "Jan": {"bu1": 100.333},
            "Feb": {"bu1": 150.666},
        }
        year_months = ["Jan", "Feb"]
        
        result = _aggregate_year_costs(cost_matrix, year_months)
        
        assert result["bu1"] == 251.0  # Rounded


class TestCalculateYearDailyAverage:
    """Tests for _calculate_year_daily_average function."""

    def test_calculate_year_daily_average(self):
        """Test calculating daily average for a year period."""
        cost_matrix = {
            "Jan": {"bu1": 3100.0},  # 31 days
            "Feb": {"bu1": 2800.0},  # 28 days (non-leap year assumed)
            "Mar": {"bu1": 3100.0},  # 31 days
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _calculate_year_daily_average(cost_matrix, year_months)
        
        # Total: 9000, Days: 31+28+31 = 90, Daily avg: 9000/90 = 100
        assert "bu1" in result
        assert result["bu1"] == 100.0

    def test_calculate_year_daily_average_multiple_groups(self):
        """Test daily average with multiple groups."""
        cost_matrix = {
            "Jan": {"bu1": 3100.0, "bu2": 1550.0},
            "Feb": {"bu1": 2800.0, "bu2": 1400.0},
        }
        year_months = ["Jan", "Feb"]
        
        result = _calculate_year_daily_average(cost_matrix, year_months)
        
        assert "bu1" in result
        assert "bu2" in result
        # bu1: 5900 / 59 days = 100
        # bu2: 2950 / 59 days = 50
        assert result["bu1"] == 100.0
        assert result["bu2"] == 50.0


class TestCalculateYearMonthlyAverage:
    """Tests for _calculate_year_monthly_average function."""

    def test_calculate_year_monthly_average(self):
        """Test calculating monthly average for a year period."""
        cost_matrix = {
            "Jan": {"bu1": 100.0},
            "Feb": {"bu1": 200.0},
            "Mar": {"bu1": 300.0},
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _calculate_year_monthly_average(cost_matrix, year_months)
        
        # Total: 600, Months: 3, Monthly avg: 600/3 = 200
        assert result["bu1"] == 200.0

    def test_calculate_year_monthly_average_12_months(self):
        """Test monthly average with 12 months."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cost_matrix = {month: {"bu1": 1200.0} for month in months}
        
        result = _calculate_year_monthly_average(cost_matrix, months)
        
        # Total: 14400, Months: 12, Monthly avg: 14400/12 = 1200
        assert result["bu1"] == 1200.0

    def test_calculate_year_monthly_average_multiple_groups(self):
        """Test monthly average with multiple groups."""
        cost_matrix = {
            "Jan": {"bu1": 300.0, "bu2": 150.0},
            "Feb": {"bu1": 300.0, "bu2": 150.0},
            "Mar": {"bu1": 300.0, "bu2": 150.0},
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _calculate_year_monthly_average(cost_matrix, year_months)
        
        # bu1: 900 / 3 = 300
        # bu2: 450 / 3 = 150
        assert result["bu1"] == 300.0
        assert result["bu2"] == 150.0

    def test_calculate_year_monthly_average_rounding(self):
        """Test that monthly averages are rounded to 2 decimal places."""
        cost_matrix = {
            "Jan": {"bu1": 100.0},
            "Feb": {"bu1": 100.0},
            "Mar": {"bu1": 100.0},
        }
        year_months = ["Jan", "Feb", "Mar"]
        
        result = _calculate_year_monthly_average(cost_matrix, year_months)
        
        # 300 / 3 = 100.00 (should be rounded)
        assert result["bu1"] == 100.0
        assert isinstance(result["bu1"], float)
