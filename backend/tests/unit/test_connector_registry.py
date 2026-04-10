"""
Unit Tests for Connector Registry

Tests that all connectors are properly registered and accessible.
"""

import pytest


class TestConnectorRegistry:
    """Test connector registration and factory functions."""

    @pytest.mark.unit
    def test_s3_connector_registered(self):
        """S3 connector should be registered in CONNECTORS dict."""
        from connectors import CONNECTORS

        assert "s3" in CONNECTORS

    @pytest.mark.unit
    def test_s3_connector_class_type(self):
        """S3 connector should be the correct class type."""
        from connectors import CONNECTORS
        from connectors.s3 import S3Connector

        assert CONNECTORS["s3"] == S3Connector

    @pytest.mark.unit
    def test_get_connector_returns_s3(self):
        """get_connector should return S3Connector instance for 's3'."""
        from connectors import get_connector
        from connectors.s3 import S3Connector

        connector = get_connector("s3")
        assert isinstance(connector, S3Connector)

    @pytest.mark.unit
    def test_get_connector_raises_for_unknown(self):
        """get_connector should raise ValueError for unknown type."""
        from connectors import get_connector

        with pytest.raises(ValueError, match="Unknown connector type"):
            get_connector("nonexistent_connector")

    @pytest.mark.unit
    def test_all_connectors_registered(self):
        """All expected connectors should be registered."""
        from connectors import CONNECTORS

        expected_connectors = [
            "file_upload",
            "google_drive",
            "box",
            "dropbox",
            "github",
            "onedrive",
            "sharepoint",
            "notion",
            "sftp",
            "web",
            "s3",  # Newly added
        ]

        for connector_type in expected_connectors:
            assert connector_type in CONNECTORS, f"Missing connector: {connector_type}"

    @pytest.mark.unit
    def test_box_connector_registered(self):
        """Box connector should be registered."""
        from connectors import CONNECTORS
        from connectors.box import BoxConnector

        assert "box" in CONNECTORS
        assert CONNECTORS["box"] == BoxConnector

    @pytest.mark.unit
    def test_sftp_connector_registered(self):
        """SFTP connector should be registered."""
        from connectors import CONNECTORS
        from connectors.sftp import SFTPConnector

        assert "sftp" in CONNECTORS
        assert CONNECTORS["sftp"] == SFTPConnector


class TestConnectorManifest:
    """Test connector manifest/registry configuration."""

    @pytest.mark.unit
    def test_s3_manifest_exists(self):
        """S3 should have a manifest entry."""
        from connectors.registry import get_connector_manifest

        manifest = get_connector_manifest("s3")
        assert manifest is not None
        assert manifest["id"] == "s3"
        assert manifest["name"] == "Amazon S3"

    @pytest.mark.unit
    def test_s3_manifest_has_enterprise_flag(self):
        """S3 manifest should indicate enterprise-only."""
        from connectors.registry import get_connector_manifest

        manifest = get_connector_manifest("s3")
        assert manifest.get("enterprise_only") is True

    @pytest.mark.unit
    def test_s3_manifest_has_auth_type(self):
        """S3 manifest should specify form auth type."""
        from connectors.registry import get_connector_manifest

        manifest = get_connector_manifest("s3")
        assert manifest.get("auth_type") == "form"

    @pytest.mark.unit
    def test_s3_manifest_has_capabilities(self):
        """S3 manifest should specify capabilities."""
        from connectors.registry import get_connector_manifest

        manifest = get_connector_manifest("s3")
        capabilities = manifest.get("capabilities", [])

        assert "binary_content" in capabilities
        assert "glacier_aware" in capabilities

    @pytest.mark.unit
    def test_notion_manifest_does_not_claim_incremental_sync(self):
        """Notion should not advertise incremental sync until since-filtering exists."""
        from connectors.registry import get_connector_manifest

        manifest = get_connector_manifest("notion")
        capabilities = manifest.get("capabilities", [])

        assert "incremental_sync" not in capabilities


class TestSourceTypeEnum:
    """Test SourceType enum includes S3."""

    @pytest.mark.unit
    def test_source_type_has_s3(self):
        """SourceType enum should include S3."""
        from connectors.enhanced import SourceType

        assert hasattr(SourceType, "S3")
        assert SourceType.S3.value == "s3"

    @pytest.mark.unit
    def test_source_type_has_box(self):
        """SourceType enum should include BOX."""
        from connectors.enhanced import SourceType

        assert hasattr(SourceType, "BOX")
        assert SourceType.BOX.value == "box"
