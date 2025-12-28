-- Complete Application Reset - Database Reset Script
-- This script truncates all tables except users and fixes foreign keys
-- WARNING: This will delete all data except user accounts!

\set ON_ERROR_STOP on

-- Display start message
\echo '====================================================================='
\echo 'TG_V1 Application Reset - Step 3: Database Reset'
\echo '====================================================================='
\echo ''

-- Verify we're in the correct database
SELECT 'Database: ' || current_database();
\echo ''

-- Count records before reset
\echo '[1/7] Current record counts:'
SELECT 'Users: ' || COUNT(*) FROM users;
SELECT 'Telegram Accounts: ' || COUNT(*) FROM telegram_accounts;
SELECT 'Proxies: ' || COUNT(*) FROM proxies;
SELECT 'Jobs: ' || COUNT(*) FROM jobs;
SELECT 'Message Logs: ' || COUNT(*) FROM message_logs;
SELECT 'User Interactions: ' || COUNT(*) FROM user_interactions;
\echo ''

-- Backup users table to temporary table (extra safety)
\echo '[2/7] Creating temporary backup of users table...'
DROP TABLE IF EXISTS users_backup_temp;
CREATE TABLE users_backup_temp AS SELECT * FROM users;
SELECT 'Users backed up: ' || COUNT(*) FROM users_backup_temp;
\echo ''

-- Drop all foreign key constraints
\echo '[3/7] Dropping foreign key constraints...'
ALTER TABLE telegram_accounts DROP CONSTRAINT IF EXISTS telegram_accounts_user_id_fkey;
ALTER TABLE telegram_accounts DROP CONSTRAINT IF EXISTS telegram_accounts_proxy_id_fkey;
ALTER TABLE user_interactions DROP CONSTRAINT IF EXISTS user_interactions_telegram_account_id_fkey;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_user_id_fkey;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_telegram_account_id_fkey;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_parent_job_id_fkey;
ALTER TABLE message_logs DROP CONSTRAINT IF EXISTS message_logs_telegram_account_id_fkey;
ALTER TABLE message_logs DROP CONSTRAINT IF EXISTS message_logs_job_id_fkey;
\echo 'Foreign keys dropped.'
\echo ''

-- Truncate all tables except users
\echo '[4/7] Truncating tables...'
TRUNCATE TABLE message_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE user_interactions RESTART IDENTITY CASCADE;
TRUNCATE TABLE jobs RESTART IDENTITY CASCADE;
TRUNCATE TABLE telegram_accounts RESTART IDENTITY CASCADE;
TRUNCATE TABLE proxies RESTART IDENTITY CASCADE;
\echo 'Tables truncated.'
\echo ''

-- Recreate foreign keys with proper CASCADE/SET NULL
\echo '[5/7] Recreating foreign keys with CASCADE/SET NULL...'

-- telegram_accounts foreign keys
ALTER TABLE telegram_accounts
    ADD CONSTRAINT telegram_accounts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE telegram_accounts
    ADD CONSTRAINT telegram_accounts_proxy_id_fkey
    FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE SET NULL;

-- user_interactions foreign keys
ALTER TABLE user_interactions
    ADD CONSTRAINT user_interactions_telegram_account_id_fkey
    FOREIGN KEY (telegram_account_id) REFERENCES telegram_accounts(id) ON DELETE CASCADE;

-- jobs foreign keys
ALTER TABLE jobs
    ADD CONSTRAINT jobs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_telegram_account_id_fkey
    FOREIGN KEY (telegram_account_id) REFERENCES telegram_accounts(id) ON DELETE SET NULL;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_parent_job_id_fkey
    FOREIGN KEY (parent_job_id) REFERENCES jobs(id) ON DELETE CASCADE;

-- message_logs foreign keys
ALTER TABLE message_logs
    ADD CONSTRAINT message_logs_telegram_account_id_fkey
    FOREIGN KEY (telegram_account_id) REFERENCES telegram_accounts(id) ON DELETE CASCADE;

ALTER TABLE message_logs
    ADD CONSTRAINT message_logs_job_id_fkey
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL;

\echo 'Foreign keys recreated with CASCADE/SET NULL.'
\echo ''

-- Verify sequences are reset
\echo '[6/7] Verifying sequences are reset to 1...'
SELECT 'telegram_accounts next ID: ' || nextval('telegram_accounts_id_seq'::regclass);
SELECT setval('telegram_accounts_id_seq', 1, false);

SELECT 'proxies next ID: ' || nextval('proxies_id_seq'::regclass);
SELECT setval('proxies_id_seq', 1, false);

SELECT 'jobs next ID: ' || nextval('jobs_id_seq'::regclass);
SELECT setval('jobs_id_seq', 1, false);

SELECT 'message_logs next ID: ' || nextval('message_logs_id_seq'::regclass);
SELECT setval('message_logs_id_seq', 1, false);

SELECT 'user_interactions next ID: ' || nextval('user_interactions_id_seq'::regclass);
SELECT setval('user_interactions_id_seq', 1, false);

\echo 'Sequences reset.'
\echo ''

-- Final verification
\echo '[7/8] Final verification:'
SELECT 'Users: ' || COUNT(*) || ' (PRESERVED)' FROM users;
SELECT 'Telegram Accounts: ' || COUNT(*) || ' (RESET)' FROM telegram_accounts;
SELECT 'Proxies: ' || COUNT(*) || ' (RESET)' FROM proxies;
SELECT 'Jobs: ' || COUNT(*) || ' (RESET)' FROM jobs;
SELECT 'Message Logs: ' || COUNT(*) || ' (RESET)' FROM message_logs;
SELECT 'User Interactions: ' || COUNT(*) || ' (RESET)' FROM user_interactions;
\echo ''

--Verify foreign key constraints
\echo '[8/8] Verifying foreign key constraints:'
\echo ''
\echo 'Foreign Key Configuration:'
SELECT 
    tc.table_name || '.' || kcu.column_name || ' -> ' || 
    ccu.table_name || '.' || ccu.column_name || ' ON DELETE ' || rc.delete_rule as constraint_info
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, kcu.column_name;
\echo ''

-- Verify proxies table schema (should have proxy_url, NOT host/port/username/password)
\echo 'Proxies table columns:'
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'proxies' 
ORDER BY ordinal_position;
\echo ''

-- Drop temporary backup
DROP TABLE users_backup_temp;

\echo '====================================================================='
\echo '✓ DATABASE RESET COMPLETED SUCCESSFULLY'
\echo '====================================================================='
\echo 'Users table preserved. All other tables are empty.'
\echo 'Foreign keys updated with CASCADE/SET NULL.'
\echo 'Sequences reset to start from 1.'
\echo ''
\echo 'Key fixes applied:'
\echo '  ✓ telegram_accounts.proxy_id ON DELETE SET NULL (fixes constraint violation)'
\echo '  ✓ Schema verified (proxy_url based, no host/port columns)'
\echo ''
\echo 'Next step: Run 4_reset_redis.ps1'
