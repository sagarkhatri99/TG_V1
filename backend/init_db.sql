-- ============================================================================
-- TG_V1 Database Initialization Script
-- This script creates the complete database schema from scratch
-- Safe to run on existing database - uses IF NOT EXISTS
-- ============================================================================

-- Create all tables in dependency order (parent tables first)

-- ============================================================================
-- 1. USERS TABLE (no dependencies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    subscription_plan VARCHAR(50) DEFAULT 'free',
    billing_cycle VARCHAR(10),
    trial_end_date TIMESTAMP,
    jobs_created_this_month INTEGER DEFAULT 0,
    job_counter_last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- ============================================================================
-- 2. PROXIES TABLE (no dependencies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS proxies (
    id SERIAL PRIMARY KEY,
    proxy_url VARCHAR(500),
    proxy_type VARCHAR(10),
    country_code VARCHAR(2),
    status VARCHAR(20) DEFAULT 'active',
    response_time INTEGER,
    last_check TIMESTAMP,
    ip_address VARCHAR(45),
    provider VARCHAR(50),
    assigned_account_id INTEGER UNIQUE
);
CREATE INDEX IF NOT EXISTS ix_proxies_id ON proxies(id);

-- ============================================================================
-- 3. TELEGRAM_ACCOUNTS TABLE (depends on users, proxies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS telegram_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    nickname VARCHAR(100),
    phone_number VARCHAR(20) UNIQUE,
    api_id VARCHAR(50),
    api_hash VARCHAR(255),
    session_string TEXT,
    proxy_id INTEGER REFERENCES proxies(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',
    trust_score FLOAT DEFAULT 50.0,
    last_activity TIMESTAMP,
    daily_message_count INTEGER DEFAULT 0,
    ban_risk_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Warmup fields
    warmup_stage VARCHAR(50) DEFAULT 'pending',
    warmup_started_at TIMESTAMP,
    warmup_completed_at TIMESTAMP,
    daily_message_limit INTEGER DEFAULT 5,
    assigned_ip VARCHAR(50),
    ip_last_verified TIMESTAMP,
    -- Campaign settings
    sleep_hour_start INTEGER DEFAULT 23,
    sleep_hour_end INTEGER DEFAULT 7
);
CREATE INDEX IF NOT EXISTS ix_telegram_accounts_id ON telegram_accounts(id);

-- ============================================================================
-- 4. JOBS TABLE (depends on users, telegram_accounts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    telegram_account_id INTEGER REFERENCES telegram_accounts(id) ON DELETE SET NULL,
    job_type VARCHAR(50),
    config TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    progress INTEGER DEFAULT 0,
    total_tasks INTEGER,
    error_message TEXT,
    celery_task_id VARCHAR(255),
    -- Enhanced tracking fields
    user_description TEXT,
    messages_sent INTEGER DEFAULT 0,
    messages_planned INTEGER DEFAULT 0,
    completion_percentage FLOAT DEFAULT 0.0,
    -- Batch distribution fields
    parent_job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    batch_number INTEGER,
    total_batches INTEGER,
    batch_user_ids TEXT
);
CREATE INDEX IF NOT EXISTS ix_jobs_id ON jobs(id);

-- ============================================================================
-- 5. USER_INTERACTIONS TABLE (depends on telegram_accounts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    telegram_account_id INTEGER REFERENCES telegram_accounts(id) ON DELETE CASCADE,
    target_user_id VARCHAR(50),
    target_username VARCHAR(100),
    last_interaction TIMESTAMP,
    interaction_count INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_user_interactions_id ON user_interactions(id);

-- ============================================================================
-- 6. MESSAGE_LOGS TABLE (depends on telegram_accounts, jobs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    telegram_account_id INTEGER REFERENCES telegram_accounts(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    target_user_id VARCHAR(50),
    target_username VARCHAR(100),
    message_content TEXT,
    ai_relevance_score FLOAT,
    delivery_status VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_message_logs_id ON message_logs(id);

-- ============================================================================
-- 7. ACTION_LOGS TABLE (depends on telegram_accounts)
-- CRITICAL: Includes all columns that were missing
-- ============================================================================
CREATE TABLE IF NOT EXISTS action_logs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES telegram_accounts(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    action_data TEXT,
    action_details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    success BOOLEAN DEFAULT TRUE NOT NULL,
    error_message TEXT,
    ban_risk_delta FLOAT
);
CREATE INDEX IF NOT EXISTS ix_action_logs_id ON action_logs(id);
CREATE INDEX IF NOT EXISTS ix_action_logs_account_id ON action_logs(account_id);
CREATE INDEX IF NOT EXISTS ix_action_logs_timestamp ON action_logs(timestamp);

-- ============================================================================
-- 8. ACCOUNT_HEALTH TABLE (depends on telegram_accounts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS account_health (
    id SERIAL PRIMARY KEY,
    account_id INTEGER UNIQUE NOT NULL REFERENCES telegram_accounts(id) ON DELETE CASCADE,
    -- Overall health
    health_score FLOAT DEFAULT 100.0,
    status VARCHAR(20) DEFAULT 'healthy',
    -- Daily counters
    messages_sent_today INTEGER DEFAULT 0,
    groups_joined_today INTEGER DEFAULT 0,
    api_calls_today INTEGER DEFAULT 0,
    last_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Error tracking
    flood_wait_count INTEGER DEFAULT 0,
    spam_error_count INTEGER DEFAULT 0,
    auth_error_count INTEGER DEFAULT 0,
    generic_error_count INTEGER DEFAULT 0,
    -- Restriction info
    is_restricted BOOLEAN DEFAULT FALSE,
    restriction_reason VARCHAR(255),
    restriction_until TIMESTAMP,
    -- Activity metadata
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_error_time TIMESTAMP,
    error_history JSON,
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_account_health_id ON account_health(id);
CREATE INDEX IF NOT EXISTS ix_account_health_account_id ON account_health(account_id);
CREATE INDEX IF NOT EXISTS ix_account_health_status ON account_health(status);
CREATE INDEX IF NOT EXISTS ix_account_health_last_activity ON account_health(last_activity);

-- ============================================================================
-- 9. MESSAGE_TEMPLATES TABLE (depends on users)
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'Custom',
    spam_risk_score FLOAT DEFAULT 0.0,
    variables JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_message_templates_id ON message_templates(id);
CREATE INDEX IF NOT EXISTS ix_message_templates_user_id ON message_templates(user_id);

-- ============================================================================
-- 16. LEAD PROFILES TABLE (no dependencies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lead_profiles (
    id SERIAL PRIMARY KEY,
    profile_name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords JSON,
    min_followers INTEGER,
    max_followers INTEGER,
    verified_only BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_lead_profiles_id ON lead_profiles(id);

-- ============================================================================
-- 17. LEADS TABLE (depends on lead_profiles)
-- ============================================================================
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES lead_profiles(id) ON DELETE SET NULL,
    telegram_user_id VARCHAR(50),
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    bio TEXT,
    follower_count INTEGER,
    is_verified BOOLEAN DEFAULT FALSE,
    last_active TIMESTAMP,
    engagement_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_leads_id ON leads(id);
CREATE INDEX IF NOT EXISTS ix_leads_profile_id ON leads(profile_id);

-- ============================================================================
-- 18. LEAD_CONVERSATIONS TABLE (depends on leads)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lead_conversations (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    message_sent BOOLEAN DEFAULT FALSE,
    message_content TEXT,
    replied BOOLEAN DEFAULT FALSE,
    reply_content TEXT,
    conversation_stage VARCHAR(50),
    last_interaction TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_lead_conversations_id ON lead_conversations(id);
CREATE INDEX IF NOT EXISTS ix_lead_conversations_lead_id ON lead_conversations(lead_id);

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
SELECT 'Database initialized successfully!' as status;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema='public';
