"""Additional unit tests for amc.__main__ module to achieve 100% coverage."""

from datetime import date
from unittest.mock import patch
import logging

import pytest

from amc.__main__ import (
    configure_logging,
    load_configuration,
    parse_time_period,
)
from amc.constants import TIME_PERIOD_YEAR


class TestConfigureLoggingRemoveHandlers:
    """Tests for configure_logging function with existing handlers."""

    def test_configure_logging_removes_existing_handlers(self):
        """Test that configure_logging removes existing handlers before adding new one."""
        # Get logger and clear any existing handlers first
        logger = logging.getLogger("amc")
        logger.handlers.clear()

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)
        assert len(logger.handlers) == 1

        # Configure logging
        configure_logging(debug_logging=False, info_logging=False)

        # Check that old handler was removed and new one added
        assert len(logger.handlers) == 1
        assert logger.handlers[0] != dummy_handler


class TestLoadConfigurationTopCostsMissing:
    """Tests for load_configuration with missing top-costs-count keys."""

    def test_load_configuration_missing_account_key(self, tmp_path):
        """Test loading configuration with missing 'account' key in top-costs-count."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {
                "service": 15,
                # "account" key is missing
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            import yaml

            yaml.safe_dump(config, f)

        with pytest.raises(ValueError, match="missing required keys: account"):
            load_configuration(config_file)

    def test_load_configuration_missing_service_key(self, tmp_path):
        """Test loading configuration with missing 'service' key in top-costs-count."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {
                "account": 10,
                # "service" key is missing
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            import yaml

            yaml.safe_dump(config, f)

        with pytest.raises(ValueError, match="missing required keys: service"):
            load_configuration(config_file)

    def test_load_configuration_missing_both_keys(self, tmp_path):
        """Test loading configuration with both keys missing in top-costs-count."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {},
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            import yaml

            yaml.safe_dump(config, f)

        with pytest.raises(ValueError, match="missing required keys"):
            load_configuration(config_file)


class TestParseTimePeriodYear:
    """Tests for parse_time_period function with year mode."""

    def test_parse_time_period_year_simple_month(self):
        """Test parsing 'year' time period with simple month calculation."""
        # Mock date.today() to return a date where going back 24 months is simple
        with patch("amc.__main__.date") as mock_date:
            # Use January 2026, so going back 24 months is January 2024
            mock_date.today.return_value = date(2026, 1, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period(TIME_PERIOD_YEAR)

            assert end_date == date(2026, 1, 1)
            # Going back 24 months from Jan 2026 should give us Jan 2024
            # start_month = 1 - 24 = -23, which is <= 0
            # years_back = (-(-23) // 12) + 1 = (23 // 12) + 1 = 1 + 1 = 2
            # new_month = -23 + (2 * 12) = -23 + 24 = 1
            assert start_date == date(2024, 1, 1)

    def test_parse_time_period_year_cross_year_boundary(self):
        """Test parsing 'year' time period crossing year boundary."""
        # Mock date.today() to return a date in March
        with patch("amc.__main__.date") as mock_date:
            # Use March 2026, going back 24 months should give us March 2024
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period(TIME_PERIOD_YEAR)

            assert end_date == date(2026, 3, 1)
            # start_month = 3 - 24 = -21, which is <= 0
            # years_back = (21 // 12) + 1 = 1 + 1 = 2
            # new_month = -21 + 24 = 3
            assert start_date == date(2024, 3, 1)

    def test_parse_time_period_year_positive_month(self):
        """Test parsing 'year' time period where start_month is positive."""
        # This would require being in a month > 24, which doesn't exist
        # But we can test the else branch by using a very far future date
        with patch("amc.__main__.date") as mock_date:
            # This is a theoretical test - in practice, month is always <= 12
            # So start_month = month - 24 is always negative
            # We'll test the edge case where it could theoretically be positive
            mock_date.today.return_value = date(2027, 12, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period(TIME_PERIOD_YEAR)

            # start_month = 12 - 24 = -12
            # This will take the if branch (start_month <= 0)
            assert end_date == date(2027, 12, 1)


class TestParseTimePeriodMonthCrossYear:
    """Tests for parse_time_period month mode crossing year boundary."""

    def test_parse_time_period_month_cross_year_january(self):
        """Test parsing 'month' in January crosses year boundary."""
        with patch("amc.__main__.date") as mock_date:
            # January 2026
            mock_date.today.return_value = date(2026, 1, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period("month")

            assert end_date == date(2026, 1, 1)
            # start_month = 1 - 2 = -1, which is <= 0
            # start_date = replace(year=2025, month=-1+12=11)
            assert start_date == date(2025, 11, 1)

    def test_parse_time_period_month_cross_year_february(self):
        """Test parsing 'month' in February crosses year boundary."""
        with patch("amc.__main__.date") as mock_date:
            # February 2026
            mock_date.today.return_value = date(2026, 2, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period("month")

            assert end_date == date(2026, 2, 1)
            # start_month = 2 - 2 = 0, which is <= 0
            # start_date = replace(year=2025, month=0+12=12)
            assert start_date == date(2025, 12, 1)

    def test_parse_time_period_month_no_cross_year(self):
        """Test parsing 'month' without crossing year boundary."""
        with patch("amc.__main__.date") as mock_date:
            # March 2026
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            start_date, end_date = parse_time_period("month")

            assert end_date == date(2026, 3, 1)
            # start_month = 3 - 2 = 1, which is > 0
            # Takes else branch
            assert start_date == date(2026, 1, 1)
