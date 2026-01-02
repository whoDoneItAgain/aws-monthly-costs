"""Unit tests for amc.__main__ module."""
import configparser
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from amc.__main__ import (
    configure_logging,
    create_aws_session,
    determine_output_formats,
    generate_output_file_path,
    load_configuration,
    parse_arguments,
    parse_time_period,
)
from amc.constants import (
    OUTPUT_FORMAT_BOTH,
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    TIME_PERIOD_PREVIOUS,
)


class TestParseArguments:
    """Tests for parse_arguments function."""

    def test_parse_arguments_with_required_profile(self):
        """Test that --profile argument is required."""
        with patch("sys.argv", ["amc"]):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_parse_arguments_with_profile(self):
        """Test parsing arguments with profile."""
        with patch("sys.argv", ["amc", "--profile", "test-profile"]):
            args = parse_arguments()
            assert args.profile == "test-profile"

    def test_parse_arguments_with_config_file(self):
        """Test parsing arguments with custom config file."""
        with patch("sys.argv", ["amc", "--profile", "test", "--config-file", "/path/to/config.yaml"]):
            args = parse_arguments()
            assert args.config_file == "/path/to/config.yaml"

    def test_parse_arguments_with_include_shared_services(self):
        """Test parsing arguments with shared services flag."""
        with patch("sys.argv", ["amc", "--profile", "test", "--include-shared-services"]):
            args = parse_arguments()
            assert args.include_shared_services is True

    def test_parse_arguments_default_values(self):
        """Test default values for optional arguments."""
        with patch("sys.argv", ["amc", "--profile", "test"]):
            args = parse_arguments()
            assert args.include_shared_services is False
            assert args.debug_logging is False
            assert args.info_logging is False
            assert args.time_period == TIME_PERIOD_PREVIOUS

    def test_parse_arguments_with_run_modes(self):
        """Test parsing arguments with custom run modes."""
        with patch("sys.argv", ["amc", "--profile", "test", "--run-modes", "account", "service"]):
            args = parse_arguments()
            assert args.run_modes == ["account", "service"]

    def test_parse_arguments_with_output_format(self):
        """Test parsing arguments with output format."""
        with patch("sys.argv", ["amc", "--profile", "test", "--output-format", "excel"]):
            args = parse_arguments()
            assert args.output_format == "excel"


class TestConfigureLogging:
    """Tests for configure_logging function."""

    @patch("amc.__main__.LOGGER")
    def test_configure_logging_debug(self, mock_logger):
        """Test logging configuration with debug enabled."""
        configure_logging(debug_logging=True, info_logging=False)
        mock_logger.setLevel.assert_called_once()

    @patch("amc.__main__.LOGGER")
    def test_configure_logging_info(self, mock_logger):
        """Test logging configuration with info enabled."""
        configure_logging(debug_logging=False, info_logging=True)
        mock_logger.setLevel.assert_called_once()

    @patch("amc.__main__.LOGGER")
    def test_configure_logging_no_logging(self, mock_logger):
        """Test logging configuration with no logging enabled."""
        configure_logging(debug_logging=False, info_logging=False)
        mock_logger.setLevel.assert_called_once()


class TestLoadConfiguration:
    """Tests for load_configuration function."""

    def test_load_configuration_success(self, sample_config, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        result = load_configuration(config_file)
        assert result == sample_config
        assert "account-groups" in result
        assert "service-aggregations" in result
        assert "top-costs-count" in result

    def test_load_configuration_file_not_found(self):
        """Test loading a non-existent configuration file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_configuration(Path("/nonexistent/config.yaml"))

    def test_load_configuration_invalid_yaml(self, tmp_path):
        """Test loading an invalid YAML file."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content:\n  - bad\n  syntax")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_configuration(config_file)

    def test_load_configuration_empty_file(self, tmp_path):
        """Test loading an empty configuration file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ValueError, match="Configuration file is empty"):
            load_configuration(config_file)

    def test_load_configuration_missing_required_keys(self, tmp_path):
        """Test loading configuration with missing required keys."""
        config_file = tmp_path / "incomplete.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump({"account-groups": {"ss": {}}}, f)

        with pytest.raises(ValueError, match="missing required keys"):
            load_configuration(config_file)

    def test_load_configuration_missing_ss_key(self, tmp_path):
        """Test loading configuration without 'ss' in account-groups."""
        config = {
            "account-groups": {"production": {}},
            "service-aggregations": {},
            "top-costs-count": {"account": 10, "service": 15},
        }
        config_file = tmp_path / "no_ss.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        with pytest.raises(ValueError, match="must contain 'ss'"):
            load_configuration(config_file)

    def test_load_configuration_invalid_top_costs_count(self, tmp_path):
        """Test loading configuration with invalid top-costs-count."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": "invalid",
        }
        config_file = tmp_path / "invalid_top_costs.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        with pytest.raises(ValueError, match="must be a dictionary"):
            load_configuration(config_file)


class TestParseTimePeriod:
    """Tests for parse_time_period function."""

    def test_parse_time_period_previous(self):
        """Test parsing 'previous' time period."""
        start_date, end_date = parse_time_period(TIME_PERIOD_PREVIOUS)
        
        # End date should be first day of current month
        today = date.today()
        expected_end = today.replace(day=1)
        assert end_date == expected_end
        
        # Start date should be first day of previous month
        if expected_end.month == 1:
            expected_start = expected_end.replace(year=expected_end.year - 1, month=1)
        else:
            expected_start = expected_end.replace(month=expected_end.month - 1)
        assert start_date == expected_start

    def test_parse_time_period_custom_range(self):
        """Test parsing custom date range."""
        start_date, end_date = parse_time_period("2024-01-01_2024-12-31")
        assert start_date == date(2024, 1, 1)
        assert end_date == date(2024, 12, 31)

    def test_parse_time_period_invalid_format(self):
        """Test parsing invalid time period format."""
        with pytest.raises(ValueError, match="Time period must be in format"):
            parse_time_period("2024-01-01")

    def test_parse_time_period_invalid_date(self):
        """Test parsing invalid date values."""
        with pytest.raises(ValueError, match="Invalid time period format"):
            parse_time_period("2024-13-01_2024-12-31")

    def test_parse_time_period_too_many_parts(self):
        """Test parsing time period with too many parts."""
        with pytest.raises(ValueError, match="Time period must be in format"):
            parse_time_period("2024-01-01_2024-06-01_2024-12-31")


class TestCreateAwsSession:
    """Tests for create_aws_session function."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_create_aws_session_success(self, mock_config_parser, mock_session):
        """Test creating AWS session successfully."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config
        
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance

        session = create_aws_session("test-profile", Path("~/.aws/config"))
        
        assert session == mock_session_instance
        mock_session.assert_called_once_with(profile_name="test-profile")

    @patch("amc.__main__.configparser.RawConfigParser")
    def test_create_aws_session_profile_not_found(self, mock_config_parser):
        """Test creating AWS session with non-existent profile."""
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_config_parser.return_value = mock_config

        with pytest.raises(Exception, match="does not exist"):
            create_aws_session("nonexistent-profile", Path("~/.aws/config"))

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_create_aws_session_invalid_credentials(self, mock_config_parser, mock_session):
        """Test creating AWS session with invalid credentials."""
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config
        
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception("Invalid credentials")
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance

        with pytest.raises(SystemExit):
            create_aws_session("test-profile", Path("~/.aws/config"))


class TestDetermineOutputFormats:
    """Tests for determine_output_formats function."""

    def test_determine_output_formats_none(self):
        """Test determine_output_formats with None."""
        result = determine_output_formats(None)
        assert result == []

    def test_determine_output_formats_csv(self):
        """Test determine_output_formats with csv."""
        result = determine_output_formats(OUTPUT_FORMAT_CSV)
        assert result == [OUTPUT_FORMAT_CSV]

    def test_determine_output_formats_excel(self):
        """Test determine_output_formats with excel."""
        result = determine_output_formats(OUTPUT_FORMAT_EXCEL)
        assert result == [OUTPUT_FORMAT_EXCEL]

    def test_determine_output_formats_both(self):
        """Test determine_output_formats with both."""
        result = determine_output_formats(OUTPUT_FORMAT_BOTH)
        assert result == [OUTPUT_FORMAT_CSV, OUTPUT_FORMAT_EXCEL]


class TestGenerateOutputFilePath:
    """Tests for generate_output_file_path function."""

    def test_generate_output_file_path_csv(self, temp_output_dir):
        """Test generating CSV output file path."""
        result = generate_output_file_path(temp_output_dir, "account", OUTPUT_FORMAT_CSV)
        assert result == temp_output_dir / "aws-monthly-costs-account.csv"

    def test_generate_output_file_path_excel(self, temp_output_dir):
        """Test generating Excel output file path."""
        result = generate_output_file_path(temp_output_dir, "service", OUTPUT_FORMAT_EXCEL)
        assert result == temp_output_dir / "aws-monthly-costs-service.xlsx"

    def test_generate_output_file_path_bu(self, temp_output_dir):
        """Test generating business unit output file path."""
        result = generate_output_file_path(temp_output_dir, "bu", OUTPUT_FORMAT_CSV)
        assert result == temp_output_dir / "aws-monthly-costs-bu.csv"
