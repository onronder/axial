-- Migration: Fix notification setting keys to match worker expectations
-- This renames old keys to new consistent naming scheme

-- Rename 'ingestion-completed' to 'inapp_on_ingestion_complete'
UPDATE user_notification_settings
SET setting_key = 'inapp_on_ingestion_complete',
    setting_label = 'Ingestion Completed',
    setting_description = 'Show in-app notification when files finish processing',
    updated_at = now()
WHERE setting_key = 'ingestion-completed';

-- Rename 'ingestion-failed' to 'inapp_on_ingestion_failed'
UPDATE user_notification_settings
SET setting_key = 'inapp_on_ingestion_failed',
    setting_label = 'Ingestion Failed',
    setting_description = 'Show in-app notification if processing fails',
    updated_at = now()
WHERE setting_key = 'ingestion-failed';

-- Log for verification
DO $$
BEGIN
    RAISE NOTICE 'Migration complete: Notification setting keys updated';
END $$;
