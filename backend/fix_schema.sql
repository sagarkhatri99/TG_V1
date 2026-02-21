-- Fix Database Schema for Telegram Automation Platform
-- Date: 2026-02-05
-- Purpose: Add missing columns and tables identified in bug analysis

-- ============================================================================
-- 1. Fix proxies table - Add missing columns
-- ============================================================================

-- Add provider column (for tracking proxy providers like webshare, iproyal, etc.)
ALTER TABLE proxies ADD COLUMN IF NOT EXISTS provider VARCHAR(50);

-- Add assigned_account_id column (for 1:1 proxy-account binding)
ALTER TABLE proxies ADD COLUMN IF NOT EXISTS assigned_account_id INTEGER;

-- Add foreign key constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_proxies_assigned_account'
    ) THEN
        ALTER TABLE proxies 
        ADD CONSTRAINT fk_proxies_assigned_account 
        FOREIGN KEY (assigned_account_id) 
        REFERENCES telegram_accounts(id) 
        ON DELETE SET NULL;
    END IF;
END $$;

-- Add unique constraint to ensure one proxy per account
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_proxies_assigned_account'
    ) THEN
        ALTER TABLE proxies 
        ADD CONSTRAINT uq_proxies_assigned_account 
        UNIQUE (assigned_account_id);
    END IF;
END $$;

-- ============================================================================
-- 2. Create message_templates table if it doesn't exist
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'Custom',
    spam_risk_score FLOAT DEFAULT 0.0,
    variables JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index on user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_message_templates_user_id ON message_templates(user_id);

-- Add updated_at column if table exists but column is missing
ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create trigger to auto-update updated_at column
CREATE OR REPLACE FUNCTION update_message_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS trigger_update_message_templates_updated_at ON message_templates;
CREATE TRIGGER trigger_update_message_templates_updated_at
    BEFORE UPDATE ON message_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_message_templates_updated_at();

-- ============================================================================
-- 3. Create campaigns table if it doesn't exist
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Add index on user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id);

-- Create trigger to auto-update updated_at column for campaigns
CREATE OR REPLACE FUNCTION update_campaigns_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS trigger_update_campaigns_updated_at ON campaigns;
CREATE TRIGGER trigger_update_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_campaigns_updated_at();

-- ============================================================================
-- 4. Verification queries
-- ============================================================================

-- Verify proxies table structure
\echo '========================================';
\echo 'Proxies table structure:';
\echo '========================================';
\d+ proxies;

-- Verify message_templates table structure
\echo '========================================';
\echo 'Message Templates table structure:';
\echo '========================================';
\d+ message_templates;

-- Verify campaigns table structure
\echo '========================================';
\echo 'Campaigns table structure:';
\echo '========================================';
\d+ campaigns;

-- ============================================================================
-- 5. Summary
-- ============================================================================

\echo '========================================';
\echo 'Schema fixes completed successfully!';
\echo '========================================';
\echo 'Changes applied:';
\echo '  ✓ Added provider column to proxies';
\echo '  ✓ Added assigned_account_id column to proxies';
\echo '  ✓ Created message_templates table (if missing)';
\echo '  ✓ Added updated_at to message_templates';
\echo '  ✓ Created campaigns table (if missing)';
\echo '  ✓ Added auto-update triggers for timestamps';
\echo '========================================';
