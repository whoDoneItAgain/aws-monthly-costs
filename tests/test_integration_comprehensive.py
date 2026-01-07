"""Comprehensive integration tests for 100% coverage - separate commit."""

from unittest.mock import MagicMock, patch

import yaml

from amc.__main__ import main
from amc.constants import (
    RUN_MODE_ACCOUNT_DAILY,
    RUN_MODE_BUSINESS_UNIT_DAILY,
    RUN_MODE_SERVICE_DAILY,
    TIME_PERIOD_YEAR,
)


class TestDailyModesIntegration:
    """Integration tests for daily average calculation modes."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_account_daily_mode_integration(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test running account-daily mode end-to-end."""
        # Setup config file
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        # Setup AWS config
        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        # Mock command line arguments
        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--run-modes",
            RUN_MODE_ACCOUNT_DAILY,
        ]

        # Mock AWS config parser
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        # Mock AWS session and clients
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}
                            },
                        }
                    ],
                },
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
                },
            ]
        }

        mock_orgs = MagicMock()
        mock_orgs.list_accounts.return_value = {
            "Accounts": [{"Id": "123456789012", "Name": "Test Account"}]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
            "organizations": mock_orgs,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            main()

        # Verify CE client was called
        assert mock_ce.get_cost_and_usage.called

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_bu_daily_mode_integration(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test running bu-daily mode end-to-end."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--run-modes",
            RUN_MODE_BUSINESS_UNIT_DAILY,
        ]

        # Setup mocks
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3100.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            main()

        assert mock_ce.get_cost_and_usage.called

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_service_daily_mode_integration(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test running service-daily mode end-to-end."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--run-modes",
            RUN_MODE_SERVICE_DAILY,
        ]

        # Setup mocks
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["AWS Lambda"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1500.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            main()

        assert mock_ce.get_cost_and_usage.called


class TestYearModeIntegration:
    """Integration tests for year analysis mode."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_year_mode_with_all_runmodes(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test year mode with all three runmodes for year analysis file generation."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--run-modes",
            "account",
            "bu",
            "service",
            "--time-period",
            TIME_PERIOD_YEAR,
        ]

        # Setup mocks
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        # Create 24 months of mock data
        mock_results = []
        for i in range(24):
            mock_results.append({
                "TimePeriod": {
                    "Start": f"2024-{(i % 12) + 1:02d}-01",
                    "End": f"2024-{((i + 1) % 12) + 1:02d}-01",
                },
                "Groups": [
                    {
                        "Keys": ["123456789012"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": f"{1000 + i * 10}.00", "Unit": "USD"}
                        },
                    }
                ],
            })

        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {"ResultsByTime": mock_results}

        mock_orgs = MagicMock()
        mock_orgs.list_accounts.return_value = {
            "Accounts": [{"Id": "123456789012", "Name": "Test Account"}]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
            "organizations": mock_orgs,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            with patch("amc.__main__._generate_year_analysis_file") as mock_year_gen:
                main()

                # Verify year analysis was called
                assert mock_year_gen.called


class TestOutputFormatsIntegration:
    """Integration tests for different output formats."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_excel_only_output(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test generating Excel-only output."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--output-format",
            "excel",
            "--run-modes",
            "account",
        ]

        # Setup mocks
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1000.00", "Unit": "USD"}
                            },
                        }
                    ],
                }
            ]
        }

        mock_orgs = MagicMock()
        mock_orgs.list_accounts.return_value = {
            "Accounts": [{"Id": "123456789012", "Name": "Test Account"}]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
            "organizations": mock_orgs,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            with patch("amc.__main__.export_report") as mock_export:
                main()

                # Verify export was called with excel format
                assert mock_export.called
                # Check that excel format was used
                call_args = mock_export.call_args_list[0]
                assert "excel" in str(call_args)
