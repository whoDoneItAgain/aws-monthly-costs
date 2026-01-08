"""Integration tests for the AWS Monthly Costs application."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from amc.__main__ import main


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_main_with_all_modes(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test running main with all three modes for analysis file generation."""
        # Setup config file
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        # Setup AWS config
        aws_config_file = tmp_path / ".aws" / "config"
        aws_config_file.parent.mkdir(parents=True)
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        # Mock command line arguments using sys.argv patch
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

        # Run main with patched argv and output folder
        with patch("sys.argv", test_args):
            with patch("amc.__main__.DEFAULT_OUTPUT_FOLDER", str(tmp_path / "outputs")):
                # This should not raise any exceptions
                try:
                    main()
                except SystemExit as e:
                    # main() may call sys.exit() which is expected
                    if e.code != 0:
                        pytest.fail(f"main() exited with non-zero code: {e.code}")

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_integration_account_mode(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test account mode integration with mocked AWS clients."""
        from amc.__main__ import (
            _process_account_mode,
            load_configuration,
        )

        # Setup config
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        # Load configuration to verify it's valid (not used, just validated)
        _config = load_configuration(config_file)

        # Mock AWS clients
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

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        analysis_data = {"account": None, "bu": None, "service": None}

        # Run account mode
        _process_account_mode(
            "account",
            mock_ce,
            mock_orgs,
            date(2024, 1, 1),
            date(2024, 2, 1),
            11,
            output_dir,
            [],
            analysis_data,
        )

        # Verify analysis_data was populated
        assert analysis_data["account"] is not None
        assert (
            len(analysis_data["account"]) == 3
        )  # (cost_matrix, account_names, account_list)

    @patch("amc.__main__.boto3.Session")
    def test_integration_bu_mode(self, mock_session, sample_config, tmp_path):
        """Test business unit mode integration with mocked AWS clients."""
        from amc.__main__ import _process_business_unit_mode

        # Mock AWS Cost Explorer client
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
                        },
                        {
                            "Keys": ["123456789015"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        analysis_data = {"account": None, "bu": None, "service": None}

        # Run business unit mode
        _process_business_unit_mode(
            "bu",
            mock_ce,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            None,
            output_dir,
            [],
            analysis_data,
        )

        # Verify analysis_data was populated
        assert analysis_data["bu"] is not None
        assert (
            len(analysis_data["bu"]) == 3
        )  # (cost_matrix, account_groups, all_account_costs)

    @patch("amc.__main__.boto3.Session")
    def test_integration_service_mode(self, mock_session, sample_config, tmp_path):
        """Test service mode integration with mocked AWS clients."""
        from amc.__main__ import _process_service_mode

        # Mock AWS Cost Explorer client
        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "800.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["Amazon S3"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        analysis_data = {"account": None, "bu": None, "service": None}

        # Run service mode
        _process_service_mode(
            "service",
            mock_ce,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["service-aggregations"],
            16,
            output_dir,
            [],
            analysis_data,
        )

        # Verify analysis_data was populated
        assert analysis_data["service"] is not None
        assert len(analysis_data["service"]) == 2  # (cost_matrix, service_list)

    def test_integration_output_file_generation(self, sample_config, tmp_path):
        """Test that CSV and Excel files are generated correctly."""
        from amc.reportexport import export_report

        cost_matrix = {
            "Jan": {"Account A": 100.00, "Account B": 200.00, "total": 300.00},
            "Feb": {"Account A": 150.00, "Account B": 250.00, "total": 400.00},
        }
        account_list = ["Account A", "Account B", "total"]

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        # Generate CSV
        csv_file = output_dir / "test.csv"
        export_report(csv_file, cost_matrix, account_list, "account", "csv")
        assert csv_file.exists()

        # Generate Excel
        excel_file = output_dir / "test.xlsx"
        export_report(excel_file, cost_matrix, account_list, "account", "excel")
        assert excel_file.exists()


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_main_without_required_profile(self):
        """Test that main exits when profile is not provided."""
        with patch("sys.argv", ["amc"]):
            with pytest.raises(SystemExit):
                from amc.__main__ import parse_arguments

                parse_arguments()

    def test_main_with_invalid_config_file(self, tmp_path):
        """Test that main handles missing config file gracefully."""
        from amc.__main__ import load_configuration

        with pytest.raises(FileNotFoundError):
            load_configuration(tmp_path / "nonexistent.yaml")

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_main_with_invalid_aws_credentials(self, mock_config_parser, mock_session):
        """Test that main handles invalid AWS credentials gracefully."""
        from amc.__main__ import create_aws_session

        # Mock AWS config parser
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config_parser.return_value = mock_config

        # Mock AWS session with invalid credentials
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception("Invalid credentials")
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_sts
        mock_session.return_value = mock_session_instance

        with pytest.raises(SystemExit):
            create_aws_session("test-profile", Path("~/.aws/config"))


class TestCrossYearBoundaryIntegration:
    """Integration tests for cross-year boundary scenarios."""

    def test_parse_time_period_december_to_january(self):
        """Test parsing time period across year boundary."""
        from amc.__main__ import parse_time_period

        # Test December to January transition
        start, end = parse_time_period("2023-12-01_2024-01-01")
        assert start.year == 2023
        assert start.month == 12
        assert end.year == 2024
        assert end.month == 1

    def test_account_costs_across_year_boundary(self):
        """Test calculating account costs across year boundary."""
        from amc.runmodes.account.calculator import _build_costs

        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2023-12-01", "End": "2024-01-01"},
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
            ]
        }

        account_list = [{"Id": "123456789012", "Name": "Test Account"}]

        result = _build_costs(response, account_list, daily_average=True)

        # December 2023 has 31 days
        assert abs(result["2023-Dec"]["Test Account"] - 100.0) < 0.01
        # January 2024 has 31 days
        assert abs(result["2024-Jan"]["Test Account"] - 100.0) < 0.01


class TestSharedServicesAllocationIntegration:
    """Integration tests for shared services allocation."""

    def test_bu_costs_without_allocation(self, sample_config):
        """Test BU costs calculation without shared services allocation."""
        from amc.runmodes.bu import calculate_business_unit_costs

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
                        },
                        {
                            "Keys": ["123456789015"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, _ = calculate_business_unit_costs(
            mock_ce,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=None,
            daily_average=False,
        )

        # Shared services should appear as separate line item
        assert result["2024-Jan"]["ss"] == 200.00
        assert result["2024-Jan"]["production"] == 1000.00

    def test_bu_costs_with_allocation(self, sample_config):
        """Test BU costs calculation with shared services allocation."""
        from amc.runmodes.bu import calculate_business_unit_costs

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
                        },
                        {
                            "Keys": ["123456789013"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "500.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789014"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "300.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["123456789015"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "200.00", "Unit": "USD"}
                            },
                        },
                    ],
                }
            ]
        }

        result, _ = calculate_business_unit_costs(
            mock_ce,
            date(2024, 1, 1),
            date(2024, 2, 1),
            sample_config["account-groups"],
            shared_services_allocations=sample_config["ss-allocations"],
            daily_average=False,
        )

        # Shared services should be allocated to BUs
        # Production: 1000 + (200 * 0.60) = 1120
        # Development: 800 + (200 * 0.40) = 880
        assert result["2024-Jan"]["production"] == 1120.00
        assert result["2024-Jan"]["development"] == 880.00
        assert result["2024-Jan"]["ss"] == 0.00  # Allocated, so 0 remaining
