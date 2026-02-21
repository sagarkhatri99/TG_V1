--
-- PostgreSQL database dump
--

\restrict jZU0bgQT3omszcE8Ms9bTmFeorfpcW5GK6FRqTr6waku0cq75313MF73PfFadPS

-- Dumped from database version 13.23 (Debian 13.23-1.pgdg13+1)
-- Dumped by pg_dump version 13.23 (Debian 13.23-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_campaigns_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_campaigns_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_message_templates_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_message_templates_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_health; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account_health (
    id integer NOT NULL,
    account_id integer NOT NULL,
    health_score double precision DEFAULT 100.0,
    status character varying(20) DEFAULT 'healthy'::character varying,
    messages_sent_today integer DEFAULT 0,
    groups_joined_today integer DEFAULT 0,
    api_calls_today integer DEFAULT 0,
    last_reset_date timestamp without time zone,
    flood_wait_count integer DEFAULT 0,
    spam_error_count integer DEFAULT 0,
    auth_error_count integer DEFAULT 0,
    generic_error_count integer DEFAULT 0,
    is_restricted boolean DEFAULT false,
    restriction_reason character varying(255),
    restriction_until timestamp without time zone,
    last_activity timestamp without time zone,
    last_error_time timestamp without time zone,
    error_history json,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: account_health_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.account_health_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: account_health_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.account_health_id_seq OWNED BY public.account_health.id;


--
-- Name: action_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_logs (
    id integer NOT NULL,
    account_id integer,
    action_type character varying(50),
    action_details text,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    success boolean DEFAULT true,
    action_data text,
    error_message text,
    ban_risk_delta double precision
);


--
-- Name: action_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_logs_id_seq OWNED BY public.action_logs.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: campaign_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_logs (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    campaign_user_interaction_id integer,
    action character varying(50) NOT NULL,
    phase character varying(10),
    message_number smallint,
    details json,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: campaign_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_logs_id_seq OWNED BY public.campaign_logs.id;


--
-- Name: campaign_message_tracking; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_message_tracking (
    id integer NOT NULL,
    campaign_user_interaction_id integer NOT NULL,
    message_number smallint NOT NULL,
    telegram_message_id bigint,
    idempotency_key character varying(36) NOT NULL,
    status character varying(20) DEFAULT 'sent'::character varying,
    sent_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    error_message text
);


--
-- Name: campaign_message_tracking_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_message_tracking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_message_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_message_tracking_id_seq OWNED BY public.campaign_message_tracking.id;


--
-- Name: campaign_pending_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_pending_tasks (
    id integer NOT NULL,
    campaign_user_interaction_id integer NOT NULL,
    celery_task_id character varying(255),
    task_type character varying(50) NOT NULL,
    scheduled_for timestamp without time zone NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    reason_paused character varying(255),
    retry_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: campaign_pending_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_pending_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_pending_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_pending_tasks_id_seq OWNED BY public.campaign_pending_tasks.id;


--
-- Name: campaign_replies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_replies (
    id integer NOT NULL,
    campaign_user_interaction_id integer NOT NULL,
    telegram_message_id bigint NOT NULL,
    message_text text,
    received_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: campaign_replies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_replies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_replies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_replies_id_seq OWNED BY public.campaign_replies.id;


--
-- Name: campaign_user_interactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_user_interactions (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    target_user_id character varying(50) NOT NULL,
    target_username character varying(100),
    telegram_first_name character varying(100),
    current_phase character varying(10) DEFAULT 'A'::character varying,
    status character varying(20) DEFAULT 'pending'::character varying,
    last_interaction_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: campaign_user_interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_user_interactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_user_interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_user_interactions_id_seq OWNED BY public.campaign_user_interactions.id;


--
-- Name: campaigns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaigns (
    id integer NOT NULL,
    user_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    status character varying(50) DEFAULT 'draft'::character varying,
    config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    telegram_account_id integer,
    parent_job_id integer,
    message_templates jsonb DEFAULT '[]'::jsonb,
    target_group_id bigint,
    start_at timestamp without time zone,
    end_at timestamp without time zone,
    min_delay integer DEFAULT 30,
    max_delay integer DEFAULT 60,
    daily_limit integer DEFAULT 100,
    total_targets integer DEFAULT 0,
    sent_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    reply_count integer DEFAULT 0
);


--
-- Name: campaigns_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaigns_id_seq OWNED BY public.campaigns.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id integer NOT NULL,
    telegram_account_id integer,
    job_type character varying(50),
    config text,
    status character varying(20),
    created_at timestamp without time zone,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    progress integer,
    total_tasks integer,
    error_message text,
    user_id integer,
    user_description text,
    messages_sent integer DEFAULT 0 NOT NULL,
    messages_planned integer DEFAULT 0 NOT NULL,
    completion_percentage double precision DEFAULT '0'::double precision NOT NULL,
    parent_job_id integer,
    batch_number integer,
    total_batches integer,
    batch_user_ids text
);


--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: lead_conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_conversations (
    id integer NOT NULL,
    lead_id integer NOT NULL,
    message_id character varying(50),
    direction character varying(10) NOT NULL,
    message_content text,
    ai_generated boolean,
    sentiment_score double precision,
    intent_detected character varying(100),
    "timestamp" timestamp without time zone
);


--
-- Name: lead_conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lead_conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lead_conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lead_conversations_id_seq OWNED BY public.lead_conversations.id;


--
-- Name: lead_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    name character varying(100) NOT NULL,
    keywords text,
    industry character varying(100),
    interests text,
    regions character varying(255),
    description text,
    target_groups text,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: lead_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lead_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lead_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lead_profiles_id_seq OWNED BY public.lead_profiles.id;


--
-- Name: leads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leads (
    id integer NOT NULL,
    user_id integer NOT NULL,
    lead_profile_id integer NOT NULL,
    telegram_user_id character varying(50),
    telegram_username character varying(100),
    first_name character varying(100),
    last_name character varying(100),
    bio text,
    profile_match_keywords text,
    relevance_score double precision,
    conversation_score double precision,
    status character varying(20),
    last_contacted_at timestamp without time zone,
    last_reply_at timestamp without time zone,
    source_group character varying(255),
    notes text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: leads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: leads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leads_id_seq OWNED BY public.leads.id;


--
-- Name: message_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.message_logs (
    id integer NOT NULL,
    telegram_account_id integer,
    job_id integer,
    target_user_id character varying(50),
    target_username character varying(100),
    message_content text,
    ai_relevance_score double precision,
    delivery_status character varying(20),
    "timestamp" timestamp without time zone
);


--
-- Name: message_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.message_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: message_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.message_logs_id_seq OWNED BY public.message_logs.id;


--
-- Name: message_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.message_templates (
    id integer NOT NULL,
    user_id integer NOT NULL,
    name character varying(255) NOT NULL,
    content text NOT NULL,
    category character varying(50) DEFAULT 'Custom'::character varying,
    spam_risk_score double precision DEFAULT 0.0,
    variables jsonb DEFAULT '[]'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: message_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.message_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: message_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.message_templates_id_seq OWNED BY public.message_templates.id;


--
-- Name: proxies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxies (
    id integer NOT NULL,
    proxy_url character varying(255),
    proxy_type character varying(10),
    country_code character varying(2),
    status character varying(20),
    response_time integer,
    last_check timestamp without time zone,
    ip_address character varying(45),
    provider character varying(50),
    assigned_account_id integer
);


--
-- Name: proxies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proxies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxies_id_seq OWNED BY public.proxies.id;


--
-- Name: telegram_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telegram_accounts (
    id integer NOT NULL,
    user_id integer,
    nickname character varying(100),
    phone_number character varying(20),
    api_id character varying(50),
    api_hash character varying(255),
    session_string text,
    proxy_id integer,
    status character varying(20),
    trust_score double precision,
    last_activity timestamp without time zone,
    daily_message_count integer,
    ban_risk_score double precision,
    created_at timestamp without time zone,
    warmup_stage character varying(50),
    warmup_started_at timestamp without time zone,
    warmup_completed_at timestamp without time zone,
    daily_message_limit integer DEFAULT 50,
    assigned_ip character varying(45),
    ip_last_verified timestamp without time zone,
    sleep_hour_start integer,
    sleep_hour_end integer
);


--
-- Name: telegram_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.telegram_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: telegram_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.telegram_accounts_id_seq OWNED BY public.telegram_accounts.id;


--
-- Name: user_interactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_interactions (
    id integer NOT NULL,
    telegram_account_id integer,
    target_user_id character varying(50),
    target_username character varying(100),
    last_interaction timestamp without time zone,
    interaction_count integer
);


--
-- Name: user_interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_interactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_interactions_id_seq OWNED BY public.user_interactions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    subscription_plan character varying(50),
    created_at timestamp without time zone,
    billing_cycle character varying(10),
    trial_end_date timestamp without time zone,
    jobs_created_this_month integer,
    job_counter_last_reset timestamp without time zone
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: account_health id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_health ALTER COLUMN id SET DEFAULT nextval('public.account_health_id_seq'::regclass);


--
-- Name: action_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_logs ALTER COLUMN id SET DEFAULT nextval('public.action_logs_id_seq'::regclass);


--
-- Name: campaign_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_logs ALTER COLUMN id SET DEFAULT nextval('public.campaign_logs_id_seq'::regclass);


--
-- Name: campaign_message_tracking id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_message_tracking ALTER COLUMN id SET DEFAULT nextval('public.campaign_message_tracking_id_seq'::regclass);


--
-- Name: campaign_pending_tasks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_pending_tasks ALTER COLUMN id SET DEFAULT nextval('public.campaign_pending_tasks_id_seq'::regclass);


--
-- Name: campaign_replies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_replies ALTER COLUMN id SET DEFAULT nextval('public.campaign_replies_id_seq'::regclass);


--
-- Name: campaign_user_interactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_user_interactions ALTER COLUMN id SET DEFAULT nextval('public.campaign_user_interactions_id_seq'::regclass);


--
-- Name: campaigns id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns ALTER COLUMN id SET DEFAULT nextval('public.campaigns_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: lead_conversations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_conversations ALTER COLUMN id SET DEFAULT nextval('public.lead_conversations_id_seq'::regclass);


--
-- Name: lead_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_profiles ALTER COLUMN id SET DEFAULT nextval('public.lead_profiles_id_seq'::regclass);


--
-- Name: leads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads ALTER COLUMN id SET DEFAULT nextval('public.leads_id_seq'::regclass);


--
-- Name: message_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_logs ALTER COLUMN id SET DEFAULT nextval('public.message_logs_id_seq'::regclass);


--
-- Name: message_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_templates ALTER COLUMN id SET DEFAULT nextval('public.message_templates_id_seq'::regclass);


--
-- Name: proxies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies ALTER COLUMN id SET DEFAULT nextval('public.proxies_id_seq'::regclass);


--
-- Name: telegram_accounts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_accounts ALTER COLUMN id SET DEFAULT nextval('public.telegram_accounts_id_seq'::regclass);


--
-- Name: user_interactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_interactions ALTER COLUMN id SET DEFAULT nextval('public.user_interactions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: account_health; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.account_health (id, account_id, health_score, status, messages_sent_today, groups_joined_today, api_calls_today, last_reset_date, flood_wait_count, spam_error_count, auth_error_count, generic_error_count, is_restricted, restriction_reason, restriction_until, last_activity, last_error_time, error_history, created_at, updated_at) FROM stdin;
1	1	100	healthy	0	0	0	2026-02-13 16:07:03.474457	0	0	0	0	f	\N	\N	2026-02-13 16:07:03.474477	\N	[]	2026-02-13 16:07:03.474488	2026-02-13 16:07:03.474499
2	4	100	healthy	0	0	0	2026-02-13 16:07:03.566524	0	0	0	0	f	\N	\N	2026-02-13 16:07:03.566546	\N	[]	2026-02-13 16:07:03.566557	2026-02-13 16:07:03.566566
\.


--
-- Data for Name: action_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.action_logs (id, account_id, action_type, action_details, "timestamp", success, action_data, error_message, ban_risk_delta) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
fix_proxy_nullable
\.


--
-- Data for Name: campaign_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaign_logs (id, campaign_id, campaign_user_interaction_id, action, phase, message_number, details, created_at) FROM stdin;
\.


--
-- Data for Name: campaign_message_tracking; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaign_message_tracking (id, campaign_user_interaction_id, message_number, telegram_message_id, idempotency_key, status, sent_at, error_message) FROM stdin;
\.


--
-- Data for Name: campaign_pending_tasks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaign_pending_tasks (id, campaign_user_interaction_id, celery_task_id, task_type, scheduled_for, status, reason_paused, retry_count, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: campaign_replies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaign_replies (id, campaign_user_interaction_id, telegram_message_id, message_text, received_at) FROM stdin;
\.


--
-- Data for Name: campaign_user_interactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaign_user_interactions (id, campaign_id, target_user_id, target_username, telegram_first_name, current_phase, status, last_interaction_at, created_at) FROM stdin;
\.


--
-- Data for Name: campaigns; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.campaigns (id, user_id, name, description, status, config, created_at, updated_at, started_at, completed_at, telegram_account_id, parent_job_id, message_templates, target_group_id, start_at, end_at, min_delay, max_delay, daily_limit, total_targets, sent_count, failed_count, reply_count) FROM stdin;
2	3	test1	\N	paused	{}	2026-02-17 08:34:58.046259	2026-02-20 19:11:21.926281	\N	\N	1	\N	[{"content": "Hi {bro|bru|sis} this is {test|demo} text!", "template_id": 8}]	\N	2026-02-17 08:35:01.502557	\N	15	30	\N	0	0	0	0
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.jobs (id, telegram_account_id, job_type, config, status, created_at, started_at, completed_at, progress, total_tasks, error_message, user_id, user_description, messages_sent, messages_planned, completion_percentage, parent_job_id, batch_number, total_batches, batch_user_ids) FROM stdin;
5	1	auto_promo	{"target_group": "tgnurting", "promo_message": "fsfcdvs", "interval_seconds": null, "use_random_interval": true, "min_interval": 60, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 5}	failed	2026-02-08 20:36:25.968385	2026-02-08 20:36:27.892646	\N	0	\N	Target group 'tgnurting' not found or invalid. Please check the username or ID.	3	 (restarted)	0	5	0	\N	\N	\N	\N
8	1	auto_promo	{"target_group": "tgnurturing", "promo_message": "j jb", "interval_seconds": null, "use_random_interval": true, "min_interval": 6, "max_interval": 300, "stop_after_hours": null, "rate_limit_per_hour": 2}	paused	2026-02-13 17:15:13.834629	2026-02-13 17:15:15.342573	2026-02-13 17:21:12.114162	8	\N	\N	3	\N	2	24	8.333333333333332	\N	\N	\N	\N
6	1	auto_promo	{"target_group": "tgnurting", "promo_message": "fsfcdvs", "interval_seconds": null, "use_random_interval": true, "min_interval": 60, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 5}	failed	2026-02-08 20:44:00.455229	2026-02-08 20:44:01.386065	\N	0	\N	Target group 'tgnurting' not found or invalid. Please check the username or ID.	3	 (restarted) (restarted)	0	5	0	\N	\N	\N	\N
12	4	auto_promo	{"target_group": "tgnurturing", "promo_message": "jfvuvb ", "interval_seconds": null, "use_random_interval": true, "min_interval": 6, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 1}	completed	2026-02-13 17:31:55.372112	2026-02-13 17:31:57.471188	2026-02-13 17:32:02.625954	100	\N	\N	3	\N	1	1	100	\N	\N	\N	\N
10	1	mass_dm_account	{"message": " kbk", "stop_after_hours": 1, "rate_limit_per_hour": 3, "delay_seconds": null, "min_delay_seconds": null, "max_delay_seconds": null, "csv_file_path": "/app/uploads/mass_dm_10.csv"}	paused	2026-02-13 17:19:22.300229	2026-02-13 17:21:13.081918	\N	4	\N	\N	3	\N	2	48	4.166666666666666	\N	\N	\N	\N
7	4	auto_promo	{"target_group": "tgnurturing", "promo_message": "gdfgdgd", "interval_seconds": null, "use_random_interval": true, "min_interval": 60, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 5}	paused	2026-02-08 20:53:42.196118	2026-02-08 20:53:43.944484	2026-02-08 20:58:32.942515	40	\N	\N	3	\N	2	5	40	\N	\N	\N	\N
4	1	auto_promo	{"target_group": "tgnurting", "promo_message": "fsfcdvs", "interval_seconds": null, "use_random_interval": true, "min_interval": 60, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 5}	failed	2026-02-08 20:32:37.468748	2026-02-08 20:34:27.008419	\N	0	\N	Target group 'tgnurting' not found or invalid. Please check the username or ID.	3	\N	0	5	0	\N	\N	\N	\N
15	1	scrape_users	{"group_username": "tgnurturing"}	completed	2026-02-17 08:19:07.347661	2026-02-17 08:19:08.783004	2026-02-17 08:19:16.212056	100	\N	\N	3	Scraping users from tgnurturing	48	48	100	\N	\N	\N	\N
11	1	mass_dm_account	{"message": " kbk", "stop_after_hours": 1, "rate_limit_per_hour": 3, "delay_seconds": null, "min_delay_seconds": null, "max_delay_seconds": null, "csv_file_path": "/app/uploads/mass_dm_10.csv"}	paused	2026-02-13 17:22:30.022644	2026-02-13 17:22:30.826757	\N	4	\N	\N	3	 (restarted)	2	48	4.166666666666666	\N	\N	\N	\N
9	1	scrape_users	{"group_username": "tgnurturing"}	completed	2026-02-13 17:17:03.000197	2026-02-13 17:17:03.71829	2026-02-13 17:17:11.918345	100	\N	\N	3	Scraping users from tgnurturing	48	48	100	\N	\N	\N	\N
16	4	group_monitor	{"group_usernames": ["tgnurturing"], "keywords": ["jb", "hello", "test", "bru"], "monitored_users": ["babushkaXOXO"], "limit": 100, "days": 7}	completed	2026-02-17 08:21:07.532943	2026-02-17 08:21:08.644435	2026-02-17 08:21:13.551302	100	\N	\N	3	\N	0	0	0	\N	\N	\N	\N
14	1	mass_dm_account	{"message": "Hi {bro|bru|sis} this is {test|demo} text!", "template_id": 8, "stop_after_hours": 1, "rate_limit_per_hour": 20, "delay_seconds": null, "min_delay_seconds": null, "max_delay_seconds": null, "csv_file_path": "/app/uploads/mass_dm_14.csv"}	paused	2026-02-13 18:52:40.734345	2026-02-13 18:52:42.613158	\N	10	\N	\N	3	\N	5	48	10.416666666666668	\N	\N	\N	\N
28	4	scrape_users	{"group_username": "tgnurturing"}	completed	2026-02-21 09:50:58.129713	2026-02-21 09:50:59.827995	2026-02-21 09:51:04.218924	100	\N	\N	3	Scraping users from tgnurturing	48	48	100	\N	\N	\N	\N
24	1	auto_promo	{"target_group": "tgnurturing", "promo_message": "cdscds", "interval_seconds": null, "use_random_interval": true, "min_interval": 60, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 2}	completed	2026-02-17 08:29:29.110899	2026-02-17 08:29:30.030929	2026-02-17 08:32:04.119943	100	\N	\N	3	\N	2	2	100	\N	\N	\N	\N
25	1	campaign	{'campaign_id': 2, 'min_delay': 15, 'max_delay': 30}	in_progress	2026-02-17 08:35:01.505255	\N	\N	0	\N	\N	3	Campaign: test1	0	0	0	\N	\N	\N	\N
26	1	mass_dm_account	{"message": "Hi {bro|bru|sis} this is {test|demo} text!", "template_id": 8, "stop_after_hours": null, "rate_limit_per_hour": 10, "delay_seconds": null, "min_delay_seconds": null, "max_delay_seconds": null, "csv_file_path": "/app/uploads/mass_dm_26.csv"}	paused	2026-02-17 08:40:52.849702	2026-02-17 08:40:54.338053	\N	8	\N	\N	3	\N	4	48	8.333333333333332	\N	\N	\N	\N
27	1	auto_promo	{"target_group": "tgnurturing", "promo_message": "fd", "template_id": null, "interval_seconds": null, "use_random_interval": true, "min_interval": 6, "max_interval": 300, "stop_after_hours": 1, "rate_limit_per_hour": 20}	paused	2026-02-21 09:50:45.532087	2026-02-21 09:50:47.640932	2026-02-21 09:52:09.564013	5	\N	\N	3	\N	1	20	5	\N	\N	\N	\N
\.


--
-- Data for Name: lead_conversations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lead_conversations (id, lead_id, message_id, direction, message_content, ai_generated, sentiment_score, intent_detected, "timestamp") FROM stdin;
\.


--
-- Data for Name: lead_profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lead_profiles (id, user_id, name, keywords, industry, interests, regions, description, target_groups, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: leads; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leads (id, user_id, lead_profile_id, telegram_user_id, telegram_username, first_name, last_name, bio, profile_match_keywords, relevance_score, conversation_score, status, last_contacted_at, last_reply_at, source_group, notes, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: message_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.message_logs (id, telegram_account_id, job_id, target_user_id, target_username, message_content, ai_relevance_score, delivery_status, "timestamp") FROM stdin;
\.


--
-- Data for Name: message_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.message_templates (id, user_id, name, content, category, spam_risk_score, variables, created_at, updated_at) FROM stdin;
2	3	gfd	dgdgfd	general	0	[]	2026-02-04 22:55:51.254842	2026-02-04 22:55:51.253644
3	3	gfd	dgdgfd	general	0	[]	2026-02-04 23:02:06.678531	2026-02-04 23:02:06.676204
4	3	fsf	fssvss	general	0	[]	2026-02-04 23:02:18.346164	2026-02-04 23:02:18.344991
5	3	fvdvd	fvddvfd	general	0	[]	2026-02-04 23:07:15.939855	2026-02-04 23:07:15.937865
8	3	gennral	Hi {bro|bru|sis} this is {test|demo} text!	general	0	["bro", "test", "demo", "sis", "bru"]	2026-02-08 20:22:24.75892	2026-02-08 20:22:24.762569
10	3	testsvsudva	Hello {bro|dude|friend}, this is a {test|demo} message!	general	0	["friend", "demo", "test", "bro", "dude"]	2026-02-20 20:11:31.929816	2026-02-20 20:11:31.936763
\.


--
-- Data for Name: proxies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxies (id, proxy_url, proxy_type, country_code, status, response_time, last_check, ip_address, provider, assigned_account_id) FROM stdin;
2	e12a206bc46c8258987c:f3c7ba87b45c4c3e@gw.dataimpulse.com:10001	socks5	US	active	2921	2026-02-13 17:14:45.901961	212.58.103.92	\N	\N
1	e12a206bc46c8258987c:f3c7ba87b45c4c3e@gw.dataimpulse.com:10000	socks5	US	active	2990	2026-02-20 19:08:38.767929	172.101.151.204	\N	\N
3	e12a206bc46c8258987c__cr.il:f3c7ba87b45c4c3e@gw.dataimpulse.com:10002	socks5	US	active	3994	2026-02-20 20:17:35.035198	46.116.156.11	\N	\N
\.


--
-- Data for Name: telegram_accounts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.telegram_accounts (id, user_id, nickname, phone_number, api_id, api_hash, session_string, proxy_id, status, trust_score, last_activity, daily_message_count, ban_risk_score, created_at, warmup_stage, warmup_started_at, warmup_completed_at, daily_message_limit, assigned_ip, ip_last_verified, sleep_hour_start, sleep_hour_end) FROM stdin;
4	3	Вероника	+13653975816	2040	b18441a1ff607e10a989891a5462e627	13653975816	\N	active	63	2026-02-20 19:09:50.784049	0	0.1	2026-02-07 08:54:11.924906	pending	\N	\N	20	\N	\N	23	7
1	3	Dario	+6285641920523	2040	b18441a1ff607e10a989891a5462e627	6285641920523	2	active	47	2026-02-20 20:13:15.345629	0	0.2	2026-02-04 23:05:51.278579	pending	\N	\N	50	\N	\N	23	7
\.


--
-- Data for Name: user_interactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_interactions (id, telegram_account_id, target_user_id, target_username, last_interaction, interaction_count) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, subscription_plan, created_at, billing_cycle, trial_end_date, jobs_created_this_month, job_counter_last_reset) FROM stdin;
1	free@test.com	$2b$12$b/zzFmgTQJoL91K0Boo3/e.4hnXq4Yhs8FoG3i7Aru8ydhLTWW.jW	free	2026-02-04 22:42:54.854409	\N	\N	0	2026-02-04 22:42:54.854473
2	pro@test.com	$2b$12$hne0Dye3ai1Z00N.GQqEHOknYwQmgyo/Uir24kA3oHZEp3rgoIMqG	pro	2026-02-04 22:42:55.244136	\N	\N	0	2026-02-04 22:42:55.244141
3	enterprise@test.com	$2b$12$vzap0KJklVkxWAGhK0Xf5eNuOgXK7Y.BJTFSMI3dXIBX2qVTpJ0AG	enterprise	2026-02-04 22:42:55.648311	\N	\N	0	2026-02-04 22:42:55.648315
4	admin@test.com	$2b$12$HGtn2KvVjyKkyUqEmzl7TucD9FZ5EMfmK3CUAu.gCLIFeL3DPgDI2	admin	2026-02-04 22:42:56.045382	\N	\N	0	2026-02-04 22:42:56.045386
\.


--
-- Name: account_health_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.account_health_id_seq', 5, true);


--
-- Name: action_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.action_logs_id_seq', 1, false);


--
-- Name: campaign_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaign_logs_id_seq', 1, false);


--
-- Name: campaign_message_tracking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaign_message_tracking_id_seq', 1, false);


--
-- Name: campaign_pending_tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaign_pending_tasks_id_seq', 1, false);


--
-- Name: campaign_replies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaign_replies_id_seq', 1, false);


--
-- Name: campaign_user_interactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaign_user_interactions_id_seq', 1, false);


--
-- Name: campaigns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.campaigns_id_seq', 2, true);


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.jobs_id_seq', 28, true);


--
-- Name: lead_conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.lead_conversations_id_seq', 1, false);


--
-- Name: lead_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.lead_profiles_id_seq', 1, false);


--
-- Name: leads_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.leads_id_seq', 1, false);


--
-- Name: message_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.message_logs_id_seq', 1, false);


--
-- Name: message_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.message_templates_id_seq', 10, true);


--
-- Name: proxies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxies_id_seq', 3, true);


--
-- Name: telegram_accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.telegram_accounts_id_seq', 6, true);


--
-- Name: user_interactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_interactions_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: account_health account_health_account_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_health
    ADD CONSTRAINT account_health_account_id_key UNIQUE (account_id);


--
-- Name: account_health account_health_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_health
    ADD CONSTRAINT account_health_pkey PRIMARY KEY (id);


--
-- Name: action_logs action_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_logs
    ADD CONSTRAINT action_logs_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: campaign_logs campaign_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_logs
    ADD CONSTRAINT campaign_logs_pkey PRIMARY KEY (id);


--
-- Name: campaign_message_tracking campaign_message_tracking_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_message_tracking
    ADD CONSTRAINT campaign_message_tracking_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: campaign_message_tracking campaign_message_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_message_tracking
    ADD CONSTRAINT campaign_message_tracking_pkey PRIMARY KEY (id);


--
-- Name: campaign_pending_tasks campaign_pending_tasks_celery_task_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_pending_tasks
    ADD CONSTRAINT campaign_pending_tasks_celery_task_id_key UNIQUE (celery_task_id);


--
-- Name: campaign_pending_tasks campaign_pending_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_pending_tasks
    ADD CONSTRAINT campaign_pending_tasks_pkey PRIMARY KEY (id);


--
-- Name: campaign_replies campaign_replies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_replies
    ADD CONSTRAINT campaign_replies_pkey PRIMARY KEY (id);


--
-- Name: campaign_user_interactions campaign_user_interactions_campaign_id_target_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_user_interactions
    ADD CONSTRAINT campaign_user_interactions_campaign_id_target_user_id_key UNIQUE (campaign_id, target_user_id);


--
-- Name: campaign_user_interactions campaign_user_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_user_interactions
    ADD CONSTRAINT campaign_user_interactions_pkey PRIMARY KEY (id);


--
-- Name: campaigns campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: lead_conversations lead_conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_conversations
    ADD CONSTRAINT lead_conversations_pkey PRIMARY KEY (id);


--
-- Name: lead_profiles lead_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_profiles
    ADD CONSTRAINT lead_profiles_pkey PRIMARY KEY (id);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: message_logs message_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_logs
    ADD CONSTRAINT message_logs_pkey PRIMARY KEY (id);


--
-- Name: message_templates message_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_templates
    ADD CONSTRAINT message_templates_pkey PRIMARY KEY (id);


--
-- Name: proxies proxies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_pkey PRIMARY KEY (id);


--
-- Name: telegram_accounts telegram_accounts_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_phone_number_key UNIQUE (phone_number);


--
-- Name: telegram_accounts telegram_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_pkey PRIMARY KEY (id);


--
-- Name: proxies uq_proxies_assigned_account; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT uq_proxies_assigned_account UNIQUE (assigned_account_id);


--
-- Name: user_interactions user_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_interactions
    ADD CONSTRAINT user_interactions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_action_logs_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_logs_account_id ON public.action_logs USING btree (account_id);


--
-- Name: idx_campaigns_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_campaigns_user_id ON public.campaigns USING btree (user_id);


--
-- Name: idx_message_templates_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_message_templates_user_id ON public.message_templates USING btree (user_id);


--
-- Name: ix_account_health_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_health_account_id ON public.account_health USING btree (account_id);


--
-- Name: ix_account_health_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_health_id ON public.account_health USING btree (id);


--
-- Name: ix_account_health_last_activity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_health_last_activity ON public.account_health USING btree (last_activity);


--
-- Name: ix_account_health_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_health_status ON public.account_health USING btree (status);


--
-- Name: ix_action_logs_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_action_logs_account_id ON public.action_logs USING btree (account_id);


--
-- Name: ix_action_logs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_action_logs_id ON public.action_logs USING btree (id);


--
-- Name: ix_action_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_action_logs_timestamp ON public.action_logs USING btree ("timestamp");


--
-- Name: ix_campaign_logs_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_logs_campaign_id ON public.campaign_logs USING btree (campaign_id);


--
-- Name: ix_campaign_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_logs_created_at ON public.campaign_logs USING btree (created_at);


--
-- Name: ix_campaign_logs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_logs_id ON public.campaign_logs USING btree (id);


--
-- Name: ix_campaign_logs_interaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_logs_interaction_id ON public.campaign_logs USING btree (campaign_user_interaction_id);


--
-- Name: ix_campaign_message_tracking_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_message_tracking_id ON public.campaign_message_tracking USING btree (id);


--
-- Name: ix_campaign_message_tracking_idempotency_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_message_tracking_idempotency_key ON public.campaign_message_tracking USING btree (idempotency_key);


--
-- Name: ix_campaign_message_tracking_interaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_message_tracking_interaction_id ON public.campaign_message_tracking USING btree (campaign_user_interaction_id);


--
-- Name: ix_campaign_pending_tasks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_pending_tasks_id ON public.campaign_pending_tasks USING btree (id);


--
-- Name: ix_campaign_pending_tasks_interaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_pending_tasks_interaction_id ON public.campaign_pending_tasks USING btree (campaign_user_interaction_id);


--
-- Name: ix_campaign_pending_tasks_scheduled_for; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_pending_tasks_scheduled_for ON public.campaign_pending_tasks USING btree (scheduled_for);


--
-- Name: ix_campaign_pending_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_pending_tasks_status ON public.campaign_pending_tasks USING btree (status);


--
-- Name: ix_campaign_replies_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_replies_id ON public.campaign_replies USING btree (id);


--
-- Name: ix_campaign_replies_interaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_replies_interaction_id ON public.campaign_replies USING btree (campaign_user_interaction_id);


--
-- Name: ix_campaign_user_interactions_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_user_interactions_campaign_id ON public.campaign_user_interactions USING btree (campaign_id);


--
-- Name: ix_campaign_user_interactions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_user_interactions_id ON public.campaign_user_interactions USING btree (id);


--
-- Name: ix_campaigns_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaigns_id ON public.campaigns USING btree (id);


--
-- Name: ix_campaigns_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaigns_status ON public.campaigns USING btree (status);


--
-- Name: ix_campaigns_telegram_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaigns_telegram_account_id ON public.campaigns USING btree (telegram_account_id);


--
-- Name: ix_campaigns_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaigns_user_id ON public.campaigns USING btree (user_id);


--
-- Name: ix_jobs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jobs_id ON public.jobs USING btree (id);


--
-- Name: ix_lead_conversations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_conversations_id ON public.lead_conversations USING btree (id);


--
-- Name: ix_lead_conversations_lead_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_conversations_lead_id ON public.lead_conversations USING btree (lead_id);


--
-- Name: ix_lead_profiles_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_profiles_id ON public.lead_profiles USING btree (id);


--
-- Name: ix_lead_profiles_keywords; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_profiles_keywords ON public.lead_profiles USING btree (keywords);


--
-- Name: ix_lead_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_profiles_user_id ON public.lead_profiles USING btree (user_id);


--
-- Name: ix_leads_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_id ON public.leads USING btree (id);


--
-- Name: ix_leads_relevance_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_relevance_score ON public.leads USING btree (relevance_score);


--
-- Name: ix_leads_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_status ON public.leads USING btree (status);


--
-- Name: ix_leads_telegram_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_telegram_user_id ON public.leads USING btree (telegram_user_id);


--
-- Name: ix_leads_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_user_id ON public.leads USING btree (user_id);


--
-- Name: ix_message_logs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_message_logs_id ON public.message_logs USING btree (id);


--
-- Name: ix_message_templates_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_message_templates_id ON public.message_templates USING btree (id);


--
-- Name: ix_message_templates_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_message_templates_user_id ON public.message_templates USING btree (user_id);


--
-- Name: ix_proxies_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxies_id ON public.proxies USING btree (id);


--
-- Name: ix_telegram_accounts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telegram_accounts_id ON public.telegram_accounts USING btree (id);


--
-- Name: ix_user_interactions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_interactions_id ON public.user_interactions USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: campaigns trigger_update_campaigns_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_campaigns_updated_at BEFORE UPDATE ON public.campaigns FOR EACH ROW EXECUTE FUNCTION public.update_campaigns_updated_at();


--
-- Name: message_templates trigger_update_message_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_message_templates_updated_at BEFORE UPDATE ON public.message_templates FOR EACH ROW EXECUTE FUNCTION public.update_message_templates_updated_at();


--
-- Name: account_health account_health_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_health
    ADD CONSTRAINT account_health_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.telegram_accounts(id) ON DELETE CASCADE;


--
-- Name: action_logs action_logs_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_logs
    ADD CONSTRAINT action_logs_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.telegram_accounts(id) ON DELETE CASCADE;


--
-- Name: campaign_logs campaign_logs_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_logs
    ADD CONSTRAINT campaign_logs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: campaign_logs campaign_logs_campaign_user_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_logs
    ADD CONSTRAINT campaign_logs_campaign_user_interaction_id_fkey FOREIGN KEY (campaign_user_interaction_id) REFERENCES public.campaign_user_interactions(id) ON DELETE CASCADE;


--
-- Name: campaign_message_tracking campaign_message_tracking_campaign_user_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_message_tracking
    ADD CONSTRAINT campaign_message_tracking_campaign_user_interaction_id_fkey FOREIGN KEY (campaign_user_interaction_id) REFERENCES public.campaign_user_interactions(id) ON DELETE CASCADE;


--
-- Name: campaign_pending_tasks campaign_pending_tasks_campaign_user_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_pending_tasks
    ADD CONSTRAINT campaign_pending_tasks_campaign_user_interaction_id_fkey FOREIGN KEY (campaign_user_interaction_id) REFERENCES public.campaign_user_interactions(id) ON DELETE CASCADE;


--
-- Name: campaign_replies campaign_replies_campaign_user_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_replies
    ADD CONSTRAINT campaign_replies_campaign_user_interaction_id_fkey FOREIGN KEY (campaign_user_interaction_id) REFERENCES public.campaign_user_interactions(id) ON DELETE CASCADE;


--
-- Name: campaign_user_interactions campaign_user_interactions_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_user_interactions
    ADD CONSTRAINT campaign_user_interactions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: campaigns campaigns_telegram_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_telegram_account_id_fkey FOREIGN KEY (telegram_account_id) REFERENCES public.telegram_accounts(id);


--
-- Name: campaigns campaigns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: jobs fk_jobs_parent_job_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT fk_jobs_parent_job_id FOREIGN KEY (parent_job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: proxies fk_proxies_assigned_account; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT fk_proxies_assigned_account FOREIGN KEY (assigned_account_id) REFERENCES public.telegram_accounts(id) ON DELETE SET NULL;


--
-- Name: jobs jobs_telegram_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_telegram_account_id_fkey FOREIGN KEY (telegram_account_id) REFERENCES public.telegram_accounts(id);


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: lead_conversations lead_conversations_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_conversations
    ADD CONSTRAINT lead_conversations_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id);


--
-- Name: lead_profiles lead_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_profiles
    ADD CONSTRAINT lead_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: leads leads_lead_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_lead_profile_id_fkey FOREIGN KEY (lead_profile_id) REFERENCES public.lead_profiles(id);


--
-- Name: leads leads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: message_logs message_logs_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_logs
    ADD CONSTRAINT message_logs_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: message_logs message_logs_telegram_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_logs
    ADD CONSTRAINT message_logs_telegram_account_id_fkey FOREIGN KEY (telegram_account_id) REFERENCES public.telegram_accounts(id);


--
-- Name: message_templates message_templates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_templates
    ADD CONSTRAINT message_templates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: telegram_accounts telegram_accounts_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


--
-- Name: telegram_accounts telegram_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_interactions user_interactions_telegram_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_interactions
    ADD CONSTRAINT user_interactions_telegram_account_id_fkey FOREIGN KEY (telegram_account_id) REFERENCES public.telegram_accounts(id);


--
-- PostgreSQL database dump complete
--

\unrestrict jZU0bgQT3omszcE8Ms9bTmFeorfpcW5GK6FRqTr6waku0cq75313MF73PfFadPS

