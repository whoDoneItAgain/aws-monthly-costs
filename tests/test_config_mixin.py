"""Unit tests for configuration mix-in functionality."""

import tempfile

import pytest

from amc.__main__ import (
    SKELETON_CONFIG_PATH,
    load_configuration,
    merge_configs,
    validate_configuration,
)


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_simple_values(self):
        """Test merging simple values."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_configs(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_top_costs_count_partial(self):
        """Test that top-costs-count allows partial specification."""
        base = {
            "top-costs-count": {"account": 10, "service": 10},
        }
        override = {
            "top-costs-count": {"account": 15},
        }
        result = merge_configs(base, override)

        # Should merge nested values for top-costs-count
        assert result["top-costs-count"]["account"] == 15
        assert result["top-costs-count"]["service"] == 10

    def test_merge_other_dicts_replaced(self):
        """Test that non-top-costs-count dicts are replaced, not merged."""
        base = {
            "account-groups": {
                "bu1": {"111111111111": {"cost-class": "opex"}},
                "ss": {"999999999999": {"cost-class": "capex"}},
            },
        }
        override = {
            "account-groups": {
                "bu2": {"222222222222": {"cost-class": "opex"}},
                "ss": {"888888888888": {"cost-class": "capex"}},
            },
        }
        result = merge_configs(base, override)

        # account-groups should be completely replaced
        assert "bu1" not in result["account-groups"]
        assert "bu2" in result["account-groups"]
        assert "111111111111" not in str(result["account-groups"])
        assert "222222222222" in str(result["account-groups"])

    def test_merge_partial_config(self):
        """Test merging partial configuration that only has account-groups."""
        base = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {"account": 10, "service": 10},
        }
        override = {
            "account-groups": {
                "bu1": {"123456789012": {"cost-class": "opex"}},
                "ss": {},
            },
        }
        result = merge_configs(base, override)

        # Override should replace account-groups
        assert "bu1" in result["account-groups"]
        # Base values for other keys should still be present
        assert result["service-aggregations"] == {}
        assert result["top-costs-count"]["account"] == 10
        assert result["top-costs-count"]["service"] == 10

    def test_merge_preserves_base(self):
        """Test that merge doesn't modify base dictionary."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 4}}

        original_base = base.copy()
        result = merge_configs(base, override)

        # Base should not be modified
        assert base == original_base
        # Result should have replaced b completely
        assert "c" not in result["b"]
        assert result["b"]["d"] == 4


class TestValidateConfiguration:
    """Tests for validate_configuration function."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {"account": 10, "service": 10},
        }
        # Should not raise
        validate_configuration(config)

    def test_validate_missing_required_keys(self):
        """Test validation fails when required keys are missing."""
        config = {
            "account-groups": {"ss": {}},
            # Missing service-aggregations and top-costs-count
        }
        with pytest.raises(ValueError, match="missing required keys"):
            validate_configuration(config)

    def test_validate_missing_ss_key(self):
        """Test validation fails when 'ss' key is missing from account-groups."""
        config = {
            "account-groups": {"bu1": {}},  # Missing 'ss'
            "service-aggregations": {},
            "top-costs-count": {"account": 10, "service": 10},
        }
        with pytest.raises(ValueError, match="must contain 'ss'"):
            validate_configuration(config)

    def test_validate_missing_top_costs_subkeys(self):
        """Test validation fails when top-costs-count is missing subkeys."""
        config = {
            "account-groups": {"ss": {}},
            "service-aggregations": {},
            "top-costs-count": {"account": 10},  # Missing 'service'
        }
        with pytest.raises(ValueError, match="missing required keys"):
            validate_configuration(config)


class TestConfigurationMixIn:
    """Integration tests for mix-in configuration loading."""

    def test_skeleton_config_loads(self):
        """Test that skeleton configuration file can be loaded."""
        config = load_configuration(SKELETON_CONFIG_PATH, validate=True)

        # Should have all required keys
        assert "account-groups" in config
        assert "service-aggregations" in config
        assert "top-costs-count" in config

        # Should have default values
        assert config["top-costs-count"]["account"] == 10
        assert config["top-costs-count"]["service"] == 10

    def test_partial_config_merge_with_skeleton(self):
        """Test merging partial config with skeleton keeps defaults."""
        # Load skeleton as base
        skeleton_config = load_configuration(SKELETON_CONFIG_PATH, validate=False)

        # Create partial override with only account-groups
        partial_config = {
            "account-groups": {
                "my-bu": {"111111111111": {"cost-class": "opex"}},
                "ss": {"999999999999": {"cost-class": "capex"}},
            }
        }

        # Merge
        result = merge_configs(skeleton_config, partial_config)

        # Should have new business unit (account-groups completely replaced)
        assert "my-bu" in result["account-groups"]

        # Should NOT have skeleton's example business unit (replaced)
        assert "your-business-unit" not in result["account-groups"]

        # Should still have default top-costs-count from skeleton
        assert result["top-costs-count"]["account"] == 10
        assert result["top-costs-count"]["service"] == 10

        # Should still have service-aggregations from skeleton
        assert "service-aggregations" in result

        # Final config should be valid
        validate_configuration(result)

    def test_cli_overrides_merge(self):
        """Test that CLI overrides work with partial specification."""
        # Load skeleton as base
        skeleton_config = load_configuration(SKELETON_CONFIG_PATH, validate=False)

        # Simulate CLI override for only top-accounts
        cli_override = {"top-costs-count": {"account": 5}}

        # Merge
        result = merge_configs(skeleton_config, cli_override)

        # Should have CLI override for account
        assert result["top-costs-count"]["account"] == 5

        # Should still have default for service
        assert result["top-costs-count"]["service"] == 10

        # Final config should be valid
        validate_configuration(result)

    def test_full_priority_chain(self):
        """Test complete priority chain: skeleton -> rc -> config-file -> cli."""
        # Create temporary config files
        with tempfile.TemporaryDirectory():
            # Load skeleton
            skeleton_config = load_configuration(SKELETON_CONFIG_PATH, validate=False)

            # Create .amcrc with top: 15
            rc_config = {"top-costs-count": {"account": 15}}

            # Create config file with top: 20
            file_config = {"top-costs-count": {"service": 20}}

            # Simulate CLI with top-accounts: 5
            cli_config = {"top-costs-count": {"account": 5}}

            # Merge in priority order
            result = skeleton_config
            result = merge_configs(result, rc_config)
            result = merge_configs(result, file_config)
            result = merge_configs(result, cli_config)

            # CLI should win for account (5)
            assert result["top-costs-count"]["account"] == 5

            # config-file should win for service (20)
            assert result["top-costs-count"]["service"] == 20

            # Final config should be valid
            validate_configuration(result)

    def test_example1_partial_rc_uses_defaults(self):
        """Example #1: .amcrc with only account-groups still uses default top 10."""
        # Load skeleton
        skeleton_config = load_configuration(SKELETON_CONFIG_PATH, validate=False)

        # .amcrc with only account-groups section
        rc_config = {
            "account-groups": {
                "my-bu": {"111111111111": {"cost-class": "opex"}},
                "ss": {"999999999999": {"cost-class": "capex"}},
            }
        }

        # Merge
        result = merge_configs(skeleton_config, rc_config)

        # Should use default top 10 from skeleton
        assert result["top-costs-count"]["account"] == 10
        assert result["top-costs-count"]["service"] == 10

        # Should have the new account-groups
        assert "my-bu" in result["account-groups"]

        # Should be valid
        validate_configuration(result)

    def test_example2_cli_overrides_rc_file(self):
        """Example #2: CLI top 5 overrides .amcrc top 15."""
        # Load skeleton
        skeleton_config = load_configuration(SKELETON_CONFIG_PATH, validate=False)

        # .amcrc says top 15
        rc_config = {"top-costs-count": {"account": 15, "service": 15}}

        # CLI says top 5
        cli_config = {"top-costs-count": {"account": 5}}

        # Merge in order
        result = merge_configs(skeleton_config, rc_config)
        result = merge_configs(result, cli_config)

        # CLI should win for account
        assert result["top-costs-count"]["account"] == 5

        # RC file should still apply for service (not overridden by CLI)
        assert result["top-costs-count"]["service"] == 15

        # Should be valid
        validate_configuration(result)
