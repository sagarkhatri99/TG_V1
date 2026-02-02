export interface Proxy {
  id: number;
  proxy_url: string;
  proxy_type: string;
  country_code: string;
  status: string;
  ip_address?: string;
  response_time?: number;
}

export interface TelegramAccount {
  id: number;
  phone_number: string;
  nickname?: string;
  status: string;
  proxy_id?: number;
  proxy?: {
    id: number;
    proxy_url: string;
    proxy_type: string;
    ip_address?: string;
  };
  trust_score: number;
  risk_score: number;
  last_activity: string;
  daily_message_count: number;
  created_at: string;
  sleep_hour_start?: number;
  sleep_hour_end?: number;
  daily_message_limit?: number;
}

export interface Campaign {
  id: number;
  user_id: number;
  telegram_account_id: number;
  name: string;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'failed';
  message_templates: string[];
  target_group_id?: string;
  min_delay: number;
  max_delay: number;
  daily_limit?: number;
  total_targets: number;
  sent_count: number;
  failed_count: number;
  reply_count: number;
  created_at: string;
  updated_at: string;
  start_at?: string;
  end_at?: string;
}

export interface CampaignStats {
  total_campaigns: number;
  active_campaigns: number;
  paused_campaigns: number;
  total_messages_sent: number;
  total_replies: number;
  avg_reply_rate: number;
}

export interface Interaction {
  id: number;
  target_user_id: string;
  telegram_first_name?: string;
  target_username?: string;
  current_phase: 'A' | 'B' | 'C' | 'D' | 'E';
  status: 'pending' | 'completed' | 'failed' | 'replied' | 'blocked';
  last_interaction_at: string;
  created_at: string;
}

export interface CampaignLog {
  id: number;
  action: string;
  phase?: string;
  message_number?: number;
  details?: any;
  created_at: string;
}

export interface WebSocketMessage {
  type: 'message_sent' | 'reply_received' | 'status_changed' | 'message_failed';
  interaction_id?: number;
  target_user?: string;
  message_text?: string;
  error?: string;
  timestamp: string;
}

export interface AccountOperatingHours {
  sleep_hour_start: number;
  sleep_hour_end: number;
  daily_message_limit?: number;
}

export interface CreateAccountRequest {
  phone_number: string;
  nickname?: string;
  proxy_id?: number;
  api_id?: string;
  api_hash?: string;
}

export interface MessageTemplate {
  id: number;
  user_id: number;
  name: string;
  content: string;
  category: string;
  spam_risk_score: number;
  variables: string[];
  created_at: string;
}

export interface CreateCampaignRequest {
  name: string;
  telegram_account_id: number;
  message_templates: string[];
  target_group_id?: string;
  manual_targets?: string[];
  min_delay: number;
  max_delay: number;
  daily_limit?: number;
  start_at?: string;
  end_at?: string;
}

export interface SystemStats {
  total_accounts: number;
  active_accounts: number;
  total_groups: number;
  monitored_groups: number;
  messages_today: number;
  system_health: string;
  system_status?: string;
  safety_features?: {
    rate_limiting: boolean;
    human_behavior: boolean;
    proxy_rotation: boolean;
  };
}

export type Template = MessageTemplate;

export interface TemplateCreate {
  name: string;
  content: string;
  category?: string;
}

export interface StartCampaignResponse {
  message: string;
  job_id: number;
  task_id: string;
  status: string;
}