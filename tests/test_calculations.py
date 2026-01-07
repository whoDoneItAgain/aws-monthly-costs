"""Unit tests for amc.reportexport.calculations module."""

import pytest

from amc.reportexport.calculations import (
    calculate_difference,
    calculate_percentage_difference,
    calculate_percentage_spend,
)


class TestCalculatePercentageDifference:
    """Tests for calculate_percentage_difference function."""

    def test_positive_increase(self):
        """Test percentage difference with positive increase."""
        result = calculate_percentage_difference(100, 150)
        assert result == 0.5  # 50% increase

    def test_positive_decrease(self):
        """Test percentage difference with decrease."""
        result = calculate_percentage_difference(150, 100)
        assert result == pytest.approx(-0.333333, rel=1e-5)

    def test_zero_baseline_positive_value(self):
        """Test percentage difference when baseline is 0 and value is positive."""
        result = calculate_percentage_difference(0, 100)
        assert result == 1.0  # 100% increase

    def test_zero_baseline_negative_value(self):
        """Test percentage difference when baseline is 0 and value is negative."""
        result = calculate_percentage_difference(0, -100)
        assert result == -1.0  # 100% decrease

    def test_both_values_zero(self):
        """Test percentage difference when both values are 0."""
        result = calculate_percentage_difference(0, 0)
        assert result == 0.0

    def test_negative_baseline_positive_value(self):
        """Test percentage difference with negative baseline and positive value."""
        # When baseline is negative, the function only checks if > 0, so it returns based on the else branch
        result = calculate_percentage_difference(-100, 50)
        assert result == 0.0  # Both conditions fail, returns 0.0

    def test_equal_values(self):
        """Test percentage difference when values are equal."""
        result = calculate_percentage_difference(100, 100)
        assert result == 0.0


class TestCalculateDifference:
    """Tests for calculate_difference function."""

    def test_positive_difference(self):
        """Test absolute difference between two positive values."""
        result = calculate_difference(100, 150)
        assert result == 50

    def test_negative_difference(self):
        """Test absolute difference when first value is larger."""
        result = calculate_difference(150, 100)
        assert result == 50

    def test_zero_difference(self):
        """Test absolute difference when values are equal."""
        result = calculate_difference(100, 100)
        assert result == 0

    def test_with_negative_values(self):
        """Test absolute difference with negative values."""
        result = calculate_difference(-50, -100)
        assert result == 50

    def test_positive_and_negative(self):
        """Test absolute difference between positive and negative values."""
        result = calculate_difference(50, -50)
        assert result == 100


class TestCalculatePercentageSpend:
    """Tests for calculate_percentage_spend function."""

    def test_normal_percentage(self):
        """Test calculating percentage of total spend."""
        result = calculate_percentage_spend(25, 100)
        assert result == 0.25

    def test_full_percentage(self):
        """Test when value equals total."""
        result = calculate_percentage_spend(100, 100)
        assert result == 1.0

    def test_zero_total(self):
        """Test when total is zero."""
        result = calculate_percentage_spend(50, 0)
        assert result == 0.0

    def test_zero_value(self):
        """Test when value is zero."""
        result = calculate_percentage_spend(0, 100)
        assert result == 0.0

    def test_small_percentage(self):
        """Test calculating small percentage."""
        result = calculate_percentage_spend(1, 1000)
        assert result == 0.001

    def test_large_value(self):
        """Test with large values."""
        result = calculate_percentage_spend(1000000, 10000000)
        assert result == 0.1
