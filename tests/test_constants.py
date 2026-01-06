"""Unit tests for amc.constants module."""

from amc.constants import (
    AWS_DIMENSION_LINKED_ACCOUNT,
    AWS_DIMENSION_SERVICE,
    AWS_GRANULARITY_MONTHLY,
    AWS_METRIC_UNBLENDED_COST,
    DEFAULT_RUN_MODES,
    KEY_SHARED_SERVICES,
    KEY_TOTAL,
    OUTPUT_FORMAT_BOTH,
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    RUN_MODE_ACCOUNT,
    RUN_MODE_ACCOUNT_DAILY,
    RUN_MODE_BUSINESS_UNIT,
    RUN_MODE_BUSINESS_UNIT_DAILY,
    RUN_MODE_SERVICE,
    RUN_MODE_SERVICE_DAILY,
    TIME_PERIOD_MONTH,
    VALID_OUTPUT_FORMATS,
    VALID_RUN_MODES,
)


class TestConstants:
    """Tests for constants module."""

    def test_run_mode_constants(self):
        """Test run mode constants are defined correctly."""
        assert RUN_MODE_ACCOUNT == "account"
        assert RUN_MODE_ACCOUNT_DAILY == "account-daily"
        assert RUN_MODE_BUSINESS_UNIT == "bu"
        assert RUN_MODE_BUSINESS_UNIT_DAILY == "bu-daily"
        assert RUN_MODE_SERVICE == "service"
        assert RUN_MODE_SERVICE_DAILY == "service-daily"

    def test_valid_run_modes(self):
        """Test valid run modes list contains all expected modes."""
        assert len(VALID_RUN_MODES) == 6
        assert RUN_MODE_ACCOUNT in VALID_RUN_MODES
        assert RUN_MODE_ACCOUNT_DAILY in VALID_RUN_MODES
        assert RUN_MODE_BUSINESS_UNIT in VALID_RUN_MODES
        assert RUN_MODE_BUSINESS_UNIT_DAILY in VALID_RUN_MODES
        assert RUN_MODE_SERVICE in VALID_RUN_MODES
        assert RUN_MODE_SERVICE_DAILY in VALID_RUN_MODES

    def test_default_run_modes(self):
        """Test default run modes contain the three main modes."""
        assert len(DEFAULT_RUN_MODES) == 3
        assert RUN_MODE_ACCOUNT in DEFAULT_RUN_MODES
        assert RUN_MODE_BUSINESS_UNIT in DEFAULT_RUN_MODES
        assert RUN_MODE_SERVICE in DEFAULT_RUN_MODES

    def test_output_format_constants(self):
        """Test output format constants are defined correctly."""
        assert OUTPUT_FORMAT_CSV == "csv"
        assert OUTPUT_FORMAT_EXCEL == "excel"
        assert OUTPUT_FORMAT_BOTH == "both"

    def test_valid_output_formats(self):
        """Test valid output formats list."""
        assert len(VALID_OUTPUT_FORMATS) == 3
        assert OUTPUT_FORMAT_CSV in VALID_OUTPUT_FORMATS
        assert OUTPUT_FORMAT_EXCEL in VALID_OUTPUT_FORMATS
        assert OUTPUT_FORMAT_BOTH in VALID_OUTPUT_FORMATS

    def test_time_period_constant(self):
        """Test time period constant."""
        assert TIME_PERIOD_MONTH == "month"

    def test_cost_aggregation_keys(self):
        """Test cost aggregation keys."""
        assert KEY_TOTAL == "total"
        assert KEY_SHARED_SERVICES == "ss"

    def test_aws_dimension_keys(self):
        """Test AWS dimension keys."""
        assert AWS_DIMENSION_LINKED_ACCOUNT == "LINKED_ACCOUNT"
        assert AWS_DIMENSION_SERVICE == "SERVICE"

    def test_aws_metrics(self):
        """Test AWS metrics constants."""
        assert AWS_METRIC_UNBLENDED_COST == "UnblendedCost"

    def test_aws_granularity(self):
        """Test AWS granularity constants."""
        assert AWS_GRANULARITY_MONTHLY == "MONTHLY"
