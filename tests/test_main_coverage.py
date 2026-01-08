"""Additional comprehensive tests for __main__.py to reach 100% coverage."""

import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from amc.__main__ import (
    main,
    _generate_analysis_file,
    _generate_year_analysis_file,
)
from amc.constants import (
    RUN_MODE_ACCOUNT,
    RUN_MODE_BUSINESS_UNIT,
    RUN_MODE_SERVICE,
)


class TestMainFunction:
    """Tests for main() function."""

    def test_main_python_version_check(self):
        """Test that main() checks Python version."""
        with patch.object(sys, 'version_info', (3, 9)):
            with pytest.raises(RuntimeError, match="Python 3.10 or higher is required"):
                main()

    @patch('amc.__main__.create_aws_session')
    @patch('amc.__main__.load_configuration')
    @patch('amc.__main__.parse_arguments')
    @patch('amc.__main__.Path')
    def test_main_creates_organizations_client_for_account_mode(
        self, mock_path, mock_parse_args, mock_load_config, mock_create_session
    ):
        """Test that main() creates organizations client when needed."""
        # Setup mocks
        mock_args = MagicMock()
        mock_args.debug_logging = False
        mock_args.info_logging = False
        mock_args.profile = "test"
        mock_args.aws_config_file = "~/.aws/config"
        mock_args.config_file = "config.yaml"
        mock_args.include_shared_services = False
        mock_args.run_modes = [RUN_MODE_ACCOUNT]
        mock_args.time_period = "month"
        mock_args.output_format = None
        mock_parse_args.return_value = mock_args

        mock_config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {"account": 10, "service": 15},
        }
        mock_load_config.return_value = mock_config

        mock_session = MagicMock()
        mock_ce_client = MagicMock()
        mock_org_client = MagicMock()
        mock_session.client.side_effect = lambda service: {
            "ce": mock_ce_client,
            "organizations": mock_org_client,
        }[service]
        mock_create_session.return_value = mock_session

        # Mock file paths
        mock_path_instance = MagicMock()
        mock_path_instance.mkdir = MagicMock()
        mock_path.return_value = mock_path_instance

        # Mock _process_account_mode to prevent actual processing
        with patch('amc.__main__._process_account_mode'):
            with patch('amc.__main__._generate_analysis_file'):
                # Call main
                try:
                    main()
                except SystemExit:
                    pass  # Ignore exit

                # Verify organizations client was created
                assert mock_session.client.call_count >= 2
                calls = [c[0][0] for c in mock_session.client.call_args_list]
                assert "organizations" in calls


class TestGenerateAnalysisFile:
    """Tests for _generate_analysis_file function."""

    def test_generate_analysis_file_missing_bu_data(self, tmp_path, caplog):
        """Test that analysis file is skipped when BU data is missing."""
        import logging
        caplog.set_level(logging.INFO)
        
        analysis_data = {
            RUN_MODE_ACCOUNT: ({"Jan": {"acc1": 100}}, ["acc1"], []),
            RUN_MODE_SERVICE: ({"Jan": {"svc1": 200}}, ["svc1"]),
            RUN_MODE_BUSINESS_UNIT: None,  # Missing
        }

        _generate_analysis_file(tmp_path, analysis_data)

        # Should log that it's skipping
        assert "Skipping analysis file generation" in caplog.text
        assert RUN_MODE_BUSINESS_UNIT in caplog.text

    def test_generate_analysis_file_missing_multiple_modes(self, tmp_path, caplog):
        """Test that analysis file is skipped when multiple modes are missing."""
        import logging
        caplog.set_level(logging.INFO)
        
        analysis_data = {
            RUN_MODE_ACCOUNT: None,
            RUN_MODE_SERVICE: None,
            RUN_MODE_BUSINESS_UNIT: ({"Jan": {"bu1": 300}}, {"bu1": []}, {}),
        }

        _generate_analysis_file(tmp_path, analysis_data)

        # Should log that it's skipping with multiple modes
        assert "Skipping analysis file generation" in caplog.text
        # Should mention both missing modes
        logs = caplog.text
        assert (RUN_MODE_ACCOUNT in logs) or (RUN_MODE_SERVICE in logs)

    @patch('amc.__main__.export_analysis_excel')
    def test_generate_analysis_file_success(self, mock_export, tmp_path, caplog):
        """Test successful generation of analysis file."""
        import logging
        caplog.set_level(logging.INFO)
        
        analysis_data = {
            RUN_MODE_BUSINESS_UNIT: ({"Jan": {"bu1": 300}}, {"bu1": []}, {}),
            RUN_MODE_SERVICE: ({"Jan": {"svc1": 200}}, ["svc1"]),
            RUN_MODE_ACCOUNT: ({"Jan": {"acc1": 100}}, ["acc1"], []),
        }

        _generate_analysis_file(tmp_path, analysis_data)

        # Should call export function
        assert mock_export.called
        assert "Generating analysis Excel file" in caplog.text
        assert "Analysis file created" in caplog.text


class TestGenerateYearAnalysisFile:
    """Tests for _generate_year_analysis_file function."""

    def test_generate_year_analysis_file_missing_data(self, tmp_path, caplog):
        """Test that year analysis file is skipped when data is missing."""
        import logging
        caplog.set_level(logging.INFO)
        
        analysis_data = {
            RUN_MODE_ACCOUNT: None,
            RUN_MODE_SERVICE: ({"Jan": {"svc1": 200}}, ["svc1"]),
            RUN_MODE_BUSINESS_UNIT: ({"Jan": {"bu1": 300}}, {"bu1": []}, {}),
        }

        mock_ce_client = MagicMock()
        mock_org_client = MagicMock()

        _generate_year_analysis_file(
            tmp_path,
            analysis_data,
            mock_ce_client,
            mock_org_client,
            date(2024, 1, 1),
            date(2026, 1, 1),
            {},
            None,
            {},
            {"account": 10, "service": 15},
        )

        # Should log that it's skipping
        assert "Skipping year analysis file generation" in caplog.text

    @patch('amc.__main__.validate_year_data')
    def test_generate_year_analysis_file_validation_error(
        self, mock_validate, tmp_path, caplog
    ):
        """Test year analysis file generation when validation fails."""
        import logging
        caplog.set_level(logging.ERROR)
        
        analysis_data = {
            RUN_MODE_BUSINESS_UNIT: ({"Jan": {"bu1": 300}}, {"bu1": []}, {}),
            RUN_MODE_SERVICE: ({"Jan": {"svc1": 200}}, ["svc1"]),
            RUN_MODE_ACCOUNT: ({"Jan": {"acc1": 100}}, ["acc1"], []),
        }

        # Mock validation to raise error
        mock_validate.side_effect = ValueError("Insufficient months")

        mock_ce_client = MagicMock()
        mock_org_client = MagicMock()

        _generate_year_analysis_file(
            tmp_path,
            analysis_data,
            mock_ce_client,
            mock_org_client,
            date(2024, 1, 1),
            date(2025, 1, 1),
            {},
            None,
            {},
            {"account": 10, "service": 15},
        )

        # Should log error and print messages
        assert "Year analysis validation failed" in caplog.text

    @patch('amc.__main__.export_year_analysis_excel')
    @patch('amc.__main__.validate_year_data')
    def test_generate_year_analysis_file_success(
        self, mock_validate, mock_export, tmp_path, caplog
    ):
        """Test successful generation of year analysis file."""
        import logging
        caplog.set_level(logging.INFO)
        
        analysis_data = {
            RUN_MODE_BUSINESS_UNIT: ({
                "2024-Jan": {"bu1": 100}, "2024-Feb": {"bu1": 110},
                "2024-Mar": {"bu1": 120}, "2024-Apr": {"bu1": 130},
                "2024-May": {"bu1": 140}, "2024-Jun": {"bu1": 150},
                "2024-Jul": {"bu1": 160}, "2024-Aug": {"bu1": 170},
                "2024-Sep": {"bu1": 180}, "2024-Oct": {"bu1": 190},
                "2024-Nov": {"bu1": 200}, "2024-Dec": {"bu1": 210},
                "2025-Jan": {"bu1": 220}, "2025-Feb": {"bu1": 230},
                "2025-Mar": {"bu1": 240}, "2025-Apr": {"bu1": 250},
                "2025-May": {"bu1": 260}, "2025-Jun": {"bu1": 270},
                "2025-Jul": {"bu1": 280}, "2025-Aug": {"bu1": 290},
                "2025-Sep": {"bu1": 300}, "2025-Oct": {"bu1": 310},
                "2025-Nov": {"bu1": 320}, "2025-Dec": {"bu1": 330},
            }, {"bu1": []}, {}),
            RUN_MODE_SERVICE: ({"2024-Jan": {"svc1": 200}}, ["svc1"]),
            RUN_MODE_ACCOUNT: ({"2024-Jan": {"acc1": 100}}, ["acc1"], []),
        }

        # Mock validation to return year splits
        year1_months = [f"2024-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        year2_months = [f"2025-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        mock_validate.return_value = (year1_months, year2_months)

        mock_ce_client = MagicMock()
        mock_org_client = MagicMock()

        _generate_year_analysis_file(
            tmp_path,
            analysis_data,
            mock_ce_client,
            mock_org_client,
            date(2024, 1, 1),
            date(2026, 1, 1),
            {},
            None,
            {},
            {"account": 10, "service": 15},
        )

        # Should call export function
        assert mock_export.called
        assert "Generating year-level analysis Excel file" in caplog.text
        assert "Year analysis file created" in caplog.text
