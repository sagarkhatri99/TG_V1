export interface TelegramAccount {
  id: number;
  nickname: string;
  phone_number: string;
  status: 'active' | 'paused' | 'pending_verification' | 'error';
  trust_score: number;
  risk_score: number;
  last_activity: string;
  daily_message_count: number;
  created_at: string;
}

export interface SystemStats {
  active_sessions: number;
  active_accounts: number;
  system_status: string;
  safety_features: {
    rate_limiting: string;
    ban_prevention: string;
    cooldown_tracking: string;
    ai_integration: string;
  };
}

export interface CreateAccountRequest {
  api_id: number;
  api_hash: string;
  phone_number: string;
  nickname: string;
}
