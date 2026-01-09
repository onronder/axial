from datetime import datetime

from models import (
    ConnectorDefinition,
    UserIntegration,
    IngestionJob,
    Notification,
    WebCrawlConfig,
    JobStatus,
    NotificationType,
    CrawlStatus,
    CrawlType,
    RefreshInterval,
    User,
)


def test_models_instantiate():
    connector = ConnectorDefinition(type="google_drive", name="Google Drive")
    integration = UserIntegration(user_id=connector.id, connector_definition_id=connector.id)
    job = IngestionJob(user_id=connector.id, provider="file_upload")
    notification = Notification(user_id=connector.id, title="Test")
    crawl = WebCrawlConfig(user_id=connector.id, root_url="https://example.com")
    user = User(id="user-1")

    assert connector.type == "google_drive"
    assert integration.connector_definition_id == connector.id
    assert job.status == "pending"
    assert notification.type == "info"
    assert crawl.status == "pending"
    assert user.id == "user-1"


def test_model_enums_values():
    assert JobStatus.COMPLETED.value == "completed"
    assert NotificationType.ERROR.value == "error"
    assert CrawlStatus.PROCESSING.value == "processing"
    assert CrawlType.SITEMAP.value == "sitemap"
    assert RefreshInterval.WEEKLY.value == "weekly"
