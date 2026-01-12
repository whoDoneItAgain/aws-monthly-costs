"""End-to-end tests with minimal mocking - tests actual file I/O and complete workflows."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from amc.__main__ import main
from amc.constants import (
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    OUTPUT_FORMAT_BOTH,
)


class TestEndToEndFileGeneration:
    """End-to-end tests that verify actual file generation."""

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_e2e_csv_file_created(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test that CSV files are actually created on disk."""
        # Setup real config file
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        # Setup real AWS config file
        aws_config_dir = tmp_path / ".aws"
        aws_config_dir.mkdir()
        aws_config_file = aws_config_dir / "config"
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        # Create real output directory
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        # Mock command line arguments
        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--output-format",
            OUTPUT_FORMAT_CSV,
            "--run-modes",
            "account",
        ]

        # Mock AWS clients
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
                },
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1100.00", "Unit": "USD"}
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

        # Run main with real file system
        with patch("sys.argv", test_args):
            with patch("amc.__main__.DEFAULT_OUTPUT_FOLDER", str(output_dir)):
                main()

        # Verify CSV file was created
        csv_file = output_dir / "aws-monthly-costs-account.csv"
        assert csv_file.exists(), "CSV file should be created"

        # Verify file has content
        content = csv_file.read_text()
        assert len(content) > 0, "CSV file should have content"
        assert "Month" in content, "CSV should have header"

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_e2e_excel_file_created(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test that Excel files are actually created on disk."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_dir = tmp_path / ".aws"
        aws_config_dir.mkdir()
        aws_config_file = aws_config_dir / "config"
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--output-format",
            OUTPUT_FORMAT_EXCEL,
            "--run-modes",
            "bu",
        ]

        # Mock AWS clients
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
                                "UnblendedCost": {"Amount": "2000.00", "Unit": "USD"}
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
                                "UnblendedCost": {"Amount": "2200.00", "Unit": "USD"}
                            },
                        }
                    ],
                },
            ]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            with patch("amc.__main__.DEFAULT_OUTPUT_FOLDER", str(output_dir)):
                main()

        # Verify Excel file was created
        excel_file = output_dir / "aws-monthly-costs-bu.xlsx"
        assert excel_file.exists(), "Excel file should be created"

        # Verify it's a valid Excel file by checking magic bytes
        with open(excel_file, "rb") as f:
            magic = f.read(4)
            # Excel files start with PK (zip format)
            assert magic[:2] == b"PK", "Excel file should be valid"

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_e2e_both_formats_created(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test that both CSV and Excel files are created when format is 'both'."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_dir = tmp_path / ".aws"
        aws_config_dir.mkdir()
        aws_config_file = aws_config_dir / "config"
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
            "--aws-config-file",
            str(aws_config_file),
            "--output-format",
            OUTPUT_FORMAT_BOTH,
            "--run-modes",
            "service",
        ]

        # Mock AWS clients
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
                                "UnblendedCost": {"Amount": "500.00", "Unit": "USD"}
                            },
                        }
                    ],
                },
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["AWS Lambda"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "550.00", "Unit": "USD"}
                            },
                        }
                    ],
                },
            ]
        }

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service: {
            "sts": mock_sts,
            "ce": mock_ce,
        }[service]
        mock_session.return_value = mock_session_instance

        with patch("sys.argv", test_args):
            with patch("amc.__main__.DEFAULT_OUTPUT_FOLDER", str(output_dir)):
                main()

        # Verify both files were created
        csv_file = output_dir / "aws-monthly-costs-service.csv"
        excel_file = output_dir / "aws-monthly-costs-service.xlsx"

        assert csv_file.exists(), "CSV file should be created"
        assert excel_file.exists(), "Excel file should be created"

    @patch("amc.__main__.boto3.Session")
    @patch("amc.__main__.configparser.RawConfigParser")
    def test_e2e_analysis_file_created(
        self, mock_config_parser, mock_session, sample_config, tmp_path
    ):
        """Test that analysis file is created when all three modes are run."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(sample_config, f)

        aws_config_dir = tmp_path / ".aws"
        aws_config_dir.mkdir()
        aws_config_file = aws_config_dir / "config"
        aws_config_file.write_text("[profile test]\nregion=us-east-1\n")

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

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

        # Mock AWS clients
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
                },
                {
                    "TimePeriod": {"Start": "2024-02-01", "End": "2024-03-01"},
                    "Groups": [
                        {
                            "Keys": ["123456789012"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1100.00", "Unit": "USD"}
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
            with patch("amc.__main__.DEFAULT_OUTPUT_FOLDER", str(output_dir)):
                main()

        # Verify analysis file was created
        analysis_file = output_dir / "aws-monthly-costs-analysis.xlsx"
        assert analysis_file.exists(), (
            "Analysis file should be created when all three modes are run"
        )


class TestEndToEndErrorScenarios:
    """End-to-end tests for error handling with real file system."""

    def test_e2e_missing_config_file(self, tmp_path):
        """Test that missing config file raises appropriate error."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(nonexistent_config),
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(
                FileNotFoundError, match="Specified configuration file not found"
            ):
                main()

    def test_e2e_invalid_yaml_config(self, tmp_path):
        """Test that invalid YAML raises appropriate error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(ValueError, match="Invalid YAML"):
                main()

    def test_e2e_empty_config_file(self, tmp_path):
        """Test that empty config file raises appropriate error."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        test_args = [
            "amc",
            "--profile",
            "test",
            "--config-file",
            str(config_file),
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(ValueError, match="Configuration file is empty"):
                main()
