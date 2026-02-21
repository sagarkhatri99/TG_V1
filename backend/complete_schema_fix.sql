-- Complete Schema Fix for Telegram Automation Platform
-- Adds all missing columns to telegram_accounts and campaigns tables
-- ============================================================================
-- 1. Fix telegram_accounts table - Add warmup and account management columns
-- ============================================================================
ALTER TABLE telegram_accounts 
  ADD COLUMN IF NOT EXISTS warmup_stage VARCHAR(50),
  ADD COLUMN IF NOT EXISTS warmup_started_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS warmup_completed_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS daily_message_limit INTEGER DEFAULT 50,
  ADD COLUMN IF NOT EXISTS assigned_ip VARCHAR(45),
  ADD COLUMN IF NOT EXISTS ip_last_verified TIMESTAMP,
  ADD COLUMN IF NOT EXISTS sleep_hour_start INTEGER,
  ADD COLUMN IF NOT EXISTS sleep_hour_end INTEGER;
-- ============================================================================
-- 2. Fix campaigns table - Add campaign management columns
-- ============================================================================
ALTER TABLE campaigns
  ADD COLUMN IF NOT EXISTS telegram_account_id INTEGER REFERENCES telegram_accounts(id),
  ADD COLUMN IF NOT EXISTS parent_job_id INTEGER,
  ADD COLUMN IF NOT EXISTS message_templates JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS target_group_id BIGINT,
  ADD COLUMN IF NOT EXISTS start_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS end_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS min_delay INTEGER DEFAULT 30,
  ADD COLUMN IF NOT EXISTS max_delay INTEGER DEFAULT 60,
  ADD COLUMN IF NOT EXISTS daily_limit INTEGER DEFAULT 100,
  ADD COLUMN IF NOT EXISTS total_targets INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sent_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failed_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS reply_count INTEGER DEFAULT 0;
-- ============================================================================
-- 3. Verification
-- ============================================================================
\echo '========================================';
\echo 'Schema fixes completed!';
\echo '========================================';
\echo 'Telegram Accounts - Added 8 columns';
\echo 'Campaigns - Added 13 columns';
\echo '========================================';
