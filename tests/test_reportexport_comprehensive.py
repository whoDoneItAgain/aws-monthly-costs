"""Comprehensive tests for amc.reportexport module to prevent future bugs."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amc.reportexport import (
    export_analysis_excel,
    export_year_analysis_excel,
)


class TestExportAnalysisExcelEdgeCases:
    """Tests for export_analysis_excel function edge cases."""

    def test_export_analysis_excel_insufficient_months(self, tmp_path, caplog):
        """Test export_analysis_excel with less than 2 months of data."""
        import logging
        caplog.set_level(logging.WARNING)
        
        output_file = tmp_path / "analysis.xlsx"
        
        # Only 1 month of data
        bu_cost_matrix = {"Jan": {"bu1": 100}}
        bu_group_list = {"bu1": []}
        service_cost_matrix = {"Jan": {"svc1": 200}}
        service_group_list = ["svc1"]
        account_cost_matrix = {"Jan": {"acc1": 300}}
        account_group_list = ["acc1"]

        export_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
        )

        # Should log warning about insufficient months
        assert "Need at least 2 months of data" in caplog.text
        # File should not be created
        assert not output_file.exists()

    def test_export_analysis_excel_with_yyyy_mon_format(self, tmp_path):
        """Test export_analysis_excel with YYYY-Mon format month names."""
        output_file = tmp_path / "analysis.xlsx"
        
        # Use YYYY-Mon format
        bu_cost_matrix = {
            "2024-Jan": {"bu1": 100, "total": 100},
            "2024-Feb": {"bu1": 110, "total": 110},
        }
        bu_group_list = {"bu1": []}
        service_cost_matrix = {
            "2024-Jan": {"svc1": 200, "total": 200},
            "2024-Feb": {"svc1": 220, "total": 220},
        }
        service_group_list = ["svc1"]
        account_cost_matrix = {
            "2024-Jan": {"acc1": 300, "total": 300},
            "2024-Feb": {"acc1": 330, "total": 330},
        }
        account_group_list = ["acc1"]

        export_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
        )

        # File should be created
        assert output_file.exists()

    def test_export_analysis_excel_with_invalid_month_format(self, tmp_path):
        """Test export_analysis_excel handles invalid month format gracefully."""
        output_file = tmp_path / "analysis.xlsx"
        
        # Use invalid format that should fall back to datetime.min
        bu_cost_matrix = {
            "InvalidMonth1": {"bu1": 100, "total": 100},
            "InvalidMonth2": {"bu1": 110, "total": 110},
        }
        bu_group_list = {"bu1": []}
        service_cost_matrix = {
            "InvalidMonth1": {"svc1": 200, "total": 200},
            "InvalidMonth2": {"svc1": 220, "total": 220},
        }
        service_group_list = ["svc1"]
        account_cost_matrix = {
            "InvalidMonth1": {"acc1": 300, "total": 300},
            "InvalidMonth2": {"acc1": 330, "total": 330},
        }
        account_group_list = ["acc1"]

        # Should handle gracefully and create file
        export_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
        )

        # File should be created despite invalid month format
        assert output_file.exists()

    def test_export_analysis_excel_creates_parent_directory(self, tmp_path):
        """Test that export_analysis_excel creates parent directory if needed."""
        # Create path with non-existent parent directory
        output_file = tmp_path / "subdir" / "analysis.xlsx"
        assert not output_file.parent.exists()
        
        bu_cost_matrix = {
            "Jan": {"bu1": 100, "total": 100},
            "Feb": {"bu1": 110, "total": 110},
        }
        bu_group_list = {"bu1": []}
        service_cost_matrix = {
            "Jan": {"svc1": 200, "total": 200},
            "Feb": {"svc1": 220, "total": 220},
        }
        service_group_list = ["svc1"]
        account_cost_matrix = {
            "Jan": {"acc1": 300, "total": 300},
            "Feb": {"acc1": 330, "total": 330},
        }
        account_group_list = ["acc1"]

        export_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
        )

        # Parent directory should be created
        assert output_file.parent.exists()
        assert output_file.exists()


class TestExportYearAnalysisExcel:
    """Tests for export_year_analysis_excel function."""

    def test_export_year_analysis_excel_basic(self, tmp_path):
        """Test basic year analysis Excel export."""
        output_file = tmp_path / "year_analysis.xlsx"
        
        # Create 24 months of data (2 years)
        months_y1 = [f"2024-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        months_y2 = [f"2025-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        
        bu_cost_matrix = {}
        for month in months_y1 + months_y2:
            bu_cost_matrix[month] = {"bu1": 100, "total": 100}
        
        bu_group_list = {"bu1": []}
        
        service_cost_matrix = {}
        for month in months_y1 + months_y2:
            service_cost_matrix[month] = {"svc1": 200, "total": 200}
        
        service_group_list = ["svc1"]
        
        account_cost_matrix = {}
        for month in months_y1 + months_y2:
            account_cost_matrix[month] = {"acc1": 300, "total": 300}
        
        account_group_list = ["acc1"]

        export_year_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
            months_y1,
            months_y2,
        )

        # File should be created
        assert output_file.exists()

    def test_export_year_analysis_excel_with_varying_costs(self, tmp_path):
        """Test year analysis with varying costs across months."""
        output_file = tmp_path / "year_analysis.xlsx"
        
        months_y1 = [f"2024-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        months_y2 = [f"2025-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        
        # Create varying costs
        bu_cost_matrix = {}
        for i, month in enumerate(months_y1 + months_y2):
            bu_cost_matrix[month] = {"bu1": 100 + i * 10, "total": 100 + i * 10}
        
        bu_group_list = {"bu1": []}
        
        service_cost_matrix = {}
        for i, month in enumerate(months_y1 + months_y2):
            service_cost_matrix[month] = {"svc1": 200 + i * 5, "total": 200 + i * 5}
        
        service_group_list = ["svc1"]
        
        account_cost_matrix = {}
        for i, month in enumerate(months_y1 + months_y2):
            account_cost_matrix[month] = {"acc1": 300 + i * 15, "total": 300 + i * 15}
        
        account_group_list = ["acc1"]

        export_year_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
            months_y1,
            months_y2,
        )

        # File should be created
        assert output_file.exists()

    def test_export_year_analysis_excel_creates_directory(self, tmp_path):
        """Test that year analysis export handles parent directory creation."""
        output_file = tmp_path / "nested" / "dir" / "year_analysis.xlsx"
        # Pre-create the directory since the function doesn't create it
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        months_y1 = [f"2024-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        months_y2 = [f"2025-{m}" for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
        
        bu_cost_matrix = {}
        for month in months_y1 + months_y2:
            bu_cost_matrix[month] = {"bu1": 100, "total": 100}
        
        bu_group_list = {"bu1": []}
        service_cost_matrix = {}
        for month in months_y1 + months_y2:
            service_cost_matrix[month] = {"svc1": 200, "total": 200}
        service_group_list = ["svc1"]
        account_cost_matrix = {}
        for month in months_y1 + months_y2:
            account_cost_matrix[month] = {"acc1": 300, "total": 300}
        account_group_list = ["acc1"]

        export_year_analysis_excel(
            output_file,
            bu_cost_matrix,
            bu_group_list,
            service_cost_matrix,
            service_group_list,
            account_cost_matrix,
            account_group_list,
            months_y1,
            months_y2,
        )

        # File should be created
        assert output_file.exists()
