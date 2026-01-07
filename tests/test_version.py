"""Unit tests for amc.version module."""

from amc.version import __version__


class TestVersion:
    """Tests for version module."""

    def test_version_exists(self):
        """Test that version is defined."""
        assert __version__ is not None

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        # Version should be in format X.Y.Z
        parts = __version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_version_is_string(self):
        """Test that version is a string."""
        assert isinstance(__version__, str)
