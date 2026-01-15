-- ============================================================================
-- Migration: Add Amazon S3 Connector Definition
-- Date: 2026-01-16
-- Description: Adds S3 connector with form-based auth support (ENTERPRISE ONLY)
-- ============================================================================

-- First, add auth_type and form_schema columns if they don't exist
-- These enable form-based authentication connectors (vs OAuth)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'connector_definitions' AND column_name = 'auth_type'
    ) THEN
        ALTER TABLE public.connector_definitions 
            ADD COLUMN auth_type TEXT DEFAULT 'oauth2';
        COMMENT ON COLUMN public.connector_definitions.auth_type IS 
            'Authentication type: oauth2, form, api_key, none';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'connector_definitions' AND column_name = 'form_schema'
    ) THEN
        ALTER TABLE public.connector_definitions 
            ADD COLUMN form_schema JSONB;
        COMMENT ON COLUMN public.connector_definitions.form_schema IS 
            'JSON schema for form-based auth connectors (dynamic form rendering)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'connector_definitions' AND column_name = 'enterprise_only'
    ) THEN
        ALTER TABLE public.connector_definitions 
            ADD COLUMN enterprise_only BOOLEAN DEFAULT false;
        COMMENT ON COLUMN public.connector_definitions.enterprise_only IS 
            'If true, connector requires Enterprise plan';
    END IF;
END $$;

-- Insert S3 connector definition
INSERT INTO public.connector_definitions (
    type, 
    name, 
    description, 
    icon_path, 
    category, 
    is_active, 
    auth_type,
    enterprise_only,
    form_schema
) VALUES (
    's3',
    'Amazon S3',
    'Connect to Amazon S3 buckets to import documents. Requires read-only IAM credentials with s3:ListBucket and s3:GetObject permissions.',
    '/icons/s3.svg',
    'cloud',
    true,
    'form',
    true,  -- ENTERPRISE ONLY
    '{
        "type": "object",
        "required": ["access_key_id", "secret_access_key", "region", "bucket_name", "prefix"],
        "properties": {
            "access_key_id": {
                "type": "string",
                "title": "AWS Access Key ID",
                "description": "Your IAM user access key (typically 20 characters)",
                "minLength": 16,
                "maxLength": 128,
                "x-input-type": "text"
            },
            "secret_access_key": {
                "type": "string",
                "title": "AWS Secret Access Key",
                "description": "Your IAM user secret key (keep this confidential)",
                "minLength": 16,
                "maxLength": 128,
                "x-input-type": "password"
            },
            "region": {
                "type": "string",
                "title": "AWS Region",
                "description": "The AWS region where your bucket is located",
                "enum": [
                    "us-east-1",
                    "us-east-2", 
                    "us-west-1",
                    "us-west-2",
                    "eu-west-1",
                    "eu-west-2",
                    "eu-west-3",
                    "eu-central-1",
                    "eu-north-1",
                    "ap-northeast-1",
                    "ap-northeast-2",
                    "ap-southeast-1",
                    "ap-southeast-2",
                    "ap-south-1",
                    "sa-east-1",
                    "ca-central-1"
                ],
                "default": "us-east-1",
                "x-input-type": "select"
            },
            "bucket_name": {
                "type": "string",
                "title": "Bucket Name",
                "description": "The S3 bucket name to connect",
                "pattern": "^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
                "minLength": 3,
                "maxLength": 63,
                "x-input-type": "text"
            },
            "prefix": {
                "type": "string",
                "title": "Folder Path (Required)",
                "description": "Folder prefix to sync (e.g., documents/ or knowledge-base/). Required to prevent expensive full-bucket scans.",
                "minLength": 1,
                "maxLength": 1024,
                "x-input-type": "text",
                "x-placeholder": "documents/"
            }
        },
        "x-iam-policy-template": {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "AxioReadOnlyS3Access",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": ["arn:aws:s3:::YOUR-BUCKET-NAME", "arn:aws:s3:::YOUR-BUCKET-NAME/*"]
            }]
        },
        "x-security-notice": "Create an IAM user with READ-ONLY access. Never grant s3:PutObject or s3:DeleteObject permissions."
    }'::jsonb
) ON CONFLICT (type) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon_path = EXCLUDED.icon_path,
    category = EXCLUDED.category,
    is_active = EXCLUDED.is_active,
    auth_type = EXCLUDED.auth_type,
    enterprise_only = EXCLUDED.enterprise_only,
    form_schema = EXCLUDED.form_schema;

-- Update existing connectors to have auth_type = 'oauth2' if not set
UPDATE public.connector_definitions 
SET auth_type = 'oauth2' 
WHERE auth_type IS NULL AND type != 's3' AND type != 'sftp';

-- Update SFTP to have auth_type = 'form'
UPDATE public.connector_definitions 
SET auth_type = 'form' 
WHERE type = 'sftp';

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload config';
