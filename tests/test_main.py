"""Unit tests for amc.__main__ module."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from amc.__main__ import (
    configure_logging,
    create_aws_session,
    determine_output_formats,
    generate_output_file_path,
    generate_skeleton_config,
    load_configuration,
    load_configuration_from_string,
    parse_arguments,
    parse_time_period,
    resolve_config_file_path,
)
from amc.constants import (
    OUTPUT_FORMAT_BOTH,
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    TIME_PERIOD_MONTH,
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
        with patch(
            "sys.argv",
            ["amc", "--profile", "test", "--config-file", "/path/to/config.yaml"],
        ):
            args = parse_arguments()
            assert args.config_file == "/path/to/config.yaml"

    def test_parse_arguments_with_include_shared_services(self):
        """Test parsing arguments with shared services flag."""
        with patch(
            "sys.argv", ["amc", "--profile", "test", "--include-shared-services"]
        ):
            args = parse_arguments()
            assert args.include_shared_services is True

    def test_parse_arguments_default_values(self):
        """Test default values for optional arguments."""
        with patch("sys.argv", ["amc", "--profile", "test"]):
            args = parse_arguments()
            assert args.include_shared_services is False
            assert args.debug_logging is False
            assert args.info_logging is False
            assert args.time_period == TIME_PERIOD_MONTH
            assert args.config_file is None
            assert args.config is None
            assert args.generate_config is None

    def test_parse_arguments_with_run_modes(self):
        """Test parsing arguments with custom run modes."""
        with patch(
            "sys.argv",
            ["amc", "--profile", "test", "--run-modes", "account", "service"],
        ):
            args = parse_arguments()
            assert args.run_modes == ["account", "service"]

    def test_parse_arguments_with_output_format(self):
        """Test parsing arguments with output format."""
        with patch(
            "sys.argv", ["amc", "--profile", "test", "--output-format", "excel"]
        ):
            args = parse_arguments()
            assert args.output_format == "excel"

    def test_parse_arguments_with_config_string(self):
        """Test parsing arguments with inline config string."""
        config_yaml = "account-groups: {ss: {}}"
        with patch("sys.argv", ["amc", "--profile", "test", "--config", config_yaml]):
            args = parse_arguments()
            assert args.config == config_yaml

    def test_parse_arguments_with_generate_config(self):
        """Test parsing arguments with generate-config option."""
        with patch(
            "sys.argv",
            ["amc", "--profile", "test", "--generate-config", "/tmp/config.yaml"],
        ):
            args = parse_arguments()
            assert args.generate_config == "/tmp/config.yaml"

    def test_parse_arguments_with_generate_config_default_path(self):
        """Test parsing arguments with generate-config without path (uses default ~/.amcrc)."""
        with patch("sys.argv", ["amc", "--generate-config"]):
            args = parse_arguments()
            assert args.generate_config == "~/.amcrc"

    def test_parse_arguments_with_generate_config_no_profile_required(self):
        """Test that --profile is not required when using --generate-config."""
        with patch("sys.argv", ["amc", "--generate-config", "/tmp/config.yaml"]):
            args = parse_arguments()
            assert args.generate_config == "/tmp/config.yaml"
            assert args.profile is None

    def test_parse_arguments_profile_required_without_generate_config(self):
        """Test that --profile is still required when not using --generate-config."""
        with patch("sys.argv", ["amc"]):
            with pytest.raises(SystemExit):
                parse_arguments()
    def test_parse_arguments_with_version(self):
        """Test that --version argument displays version and exits without requiring --profile."""
        with patch("sys.argv", ["amc", "--version"]):
            with pytest.raises(SystemExit) as excinfo:
                parse_arguments()
            # argparse exits with code 0 for --version
            assert excinfo.value.code == 0


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

    def test_parse_time_period_month(self):
        """Test parsing 'month' time period (2 full months)."""
        start_date, end_date = parse_time_period(TIME_PERIOD_MONTH)

        # End date should be first day of current month
        today = date.today()
        expected_end = today.replace(day=1)
        assert end_date == expected_end

        # Start date should be first day of 2 months ago
        start_month = expected_end.month - 2
        if start_month <= 0:
            expected_start = expected_end.replace(
                year=expected_end.year - 1, month=start_month + 12
            )
        else:
            expected_start = expected_end.replace(month=start_month)
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
    def test_create_aws_session_invalid_credentials(
        self, mock_config_parser, mock_session
    ):
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
        result = generate_output_file_path(
            temp_output_dir, "account", OUTPUT_FORMAT_CSV
        )
        assert result == temp_output_dir / "aws-monthly-costs-account.csv"

    def test_generate_output_file_path_excel(self, temp_output_dir):
        """Test generating Excel output file path."""
        result = generate_output_file_path(
            temp_output_dir, "service", OUTPUT_FORMAT_EXCEL
        )
        assert result == temp_output_dir / "aws-monthly-costs-service.xlsx"

    def test_generate_output_file_path_bu(self, temp_output_dir):
        """Test generating business unit output file path."""
        result = generate_output_file_path(temp_output_dir, "bu", OUTPUT_FORMAT_CSV)
        assert result == temp_output_dir / "aws-monthly-costs-bu.csv"


class TestResolveConfigFilePath:
    """Tests for resolve_config_file_path function."""

    def test_resolve_config_file_explicit_path_exists(self, tmp_path):
        """Test resolving config path when explicit path is provided and exists."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("test: config")

        result = resolve_config_file_path(str(config_file))
        assert result == config_file.absolute()

    def test_resolve_config_file_explicit_path_not_exists(self, tmp_path):
        """Test resolving config path when explicit path doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(
            FileNotFoundError, match="Specified configuration file not found"
        ):
            resolve_config_file_path(str(config_file))

    @patch("amc.__main__.LOGGER")
    def test_resolve_config_file_user_rc_exists(self, mock_logger, tmp_path):
        """Test resolving config path when ~/.amcrc exists."""
        user_rc_file = tmp_path / ".amcrc"
        user_rc_file.write_text("test: config")

        with patch("os.path.expanduser", return_value=str(user_rc_file)):
            result = resolve_config_file_path(None)
            assert result == user_rc_file.absolute()

    @patch("amc.__main__.LOGGER")
    def test_resolve_config_file_default(self, mock_logger, tmp_path):
        """Test resolving config path when no explicit path and no ~/.amcrc."""
        # Create a non-existent path for user RC file
        user_rc_file = tmp_path / "nonexistent" / ".amcrc"

        with patch("os.path.expanduser", return_value=str(user_rc_file)):
            result = resolve_config_file_path(None)
            # Should return None to indicate skeleton config should be used
            assert result is None


class TestLoadConfigurationFromString:
    """Tests for load_configuration_from_string function."""

    def test_load_configuration_from_string_success(self, sample_config):
        """Test loading valid configuration from YAML string."""
        config_str = yaml.dump(sample_config)
        result = load_configuration_from_string(config_str)
        assert result == sample_config
        assert "account-groups" in result
        assert "service-aggregations" in result
        assert "top-costs-count" in result

    def test_load_configuration_from_string_invalid_yaml(self):
        """Test loading invalid YAML string."""
        invalid_yaml = "invalid: yaml: content:\n  - bad\n  syntax"
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_configuration_from_string(invalid_yaml)

    def test_load_configuration_from_string_empty(self):
        """Test loading empty configuration string."""
        with pytest.raises(ValueError, match="Configuration string is empty"):
            load_configuration_from_string("")

    def test_load_configuration_from_string_missing_keys(self):
        """Test loading configuration with missing required keys."""
        incomplete_config = "account-groups:\n  ss: {}"
        with pytest.raises(ValueError, match="missing required keys"):
            load_configuration_from_string(incomplete_config)


class TestGenerateSkeletonConfig:
    """Tests for generate_skeleton_config function."""

    @patch("amc.__main__.LOGGER")
    def test_generate_skeleton_config_basic(self, mock_logger, tmp_path):
        """Test generating skeleton config file."""
        output_path = tmp_path / "test-config.yaml"

        generate_skeleton_config(str(output_path))

        assert output_path.exists()
        # Verify the file contains valid YAML
        with open(output_path) as f:
            config = yaml.safe_load(f)
        assert "account-groups" in config
        assert "ss" in config["account-groups"]
        assert "top-costs-count" in config

    @patch("amc.__main__.LOGGER")
    def test_generate_skeleton_config_with_nested_dirs(self, mock_logger, tmp_path):
        """Test generating skeleton config with nested directories."""
        output_path = tmp_path / "nested" / "dir" / "config.yaml"

        generate_skeleton_config(str(output_path))

        assert output_path.exists()
        with open(output_path) as f:
            config = yaml.safe_load(f)
        assert config is not None
