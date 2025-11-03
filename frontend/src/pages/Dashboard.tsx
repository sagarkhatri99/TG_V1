import { useEffect, useState } from 'react';
import { Typography, Box, CircularProgress } from '@mui/material';

import {
  AccountCircle,
  TrendingUp,
  Security,
  Speed,
} from '@mui/icons-material';
import api, { endpoints } from '../api/Index';
import type { SystemStats, TelegramAccount } from '../Types/Index';
import { StatsCard } from '../components/StatsCard';
import { RecentAccounts } from '../components/RecentAccounts';
import { SafetyFeatures } from '../components/SafetyFeatures';

export default function Dashboard() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [meStats, setMeStats] = useState<{
    active_accounts: number;
    active_sessions: number;
  } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, accountsResponse, meStatsResponse] =
          await Promise.all([
            api.get(endpoints.stats),
            api.get(endpoints.accounts.list),
            api.get(endpoints.me.stats),
          ]);
        setStats(statsResponse.data);
        setAccounts(accountsResponse.data.accounts || []);
        setMeStats(meStatsResponse.data);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Welcome to TG Tools. Monitor your Telegram automation activities.
      </Typography>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          flexWrap: 'wrap',
          gap: 3,
          mb: 4,
        }}
      >
        <Box
          sx={{
            flex: {
              xs: '1 1 100%',
              sm: '1 1 calc(50% - 12px)',
              md: '1 1 calc(25% - 18px)',
            },
          }}
        >
          <StatsCard
            title="Active Accounts"
            value={
              meStats?.active_accounts ??
              accounts.filter((a) => a.status === 'active').length
            }
            icon={<AccountCircle color="primary" />}
          />
        </Box>

        <Box
          sx={{
            flex: {
              xs: '1 1 100%',
              sm: '1 1 calc(50% - 12px)',
              md: '1 1 calc(25% - 18px)',
            },
          }}
        >
          <StatsCard
            title="Active Sessions"
            value={meStats?.active_sessions ?? 0}
            icon={<TrendingUp color="secondary" />}
          />
        </Box>

        <Box
          sx={{
            flex: {
              xs: '1 1 100%',
              sm: '1 1 calc(50% - 12px)',
              md: '1 1 calc(25% - 18px)',
            },
          }}
        >
          <StatsCard
            title="Safety Score"
            value="98%"
            icon={<Security color="success" />}
          />
        </Box>

        <Box
          sx={{
            flex: {
              xs: '1 1 100%',
              sm: '1 1 calc(50% - 12px)',
              md: '1 1 calc(25% - 18px)',
            },
          }}
        >
          <StatsCard
            title="System Status"
            value={stats?.system_status || 'Unknown'}
            icon={
              <Speed
                color={
                  stats?.system_status === 'operational' ? 'success' : 'warning'
                }
              />
            }
          />
        </Box>
      </Box>

      <Box
        sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}
      >
        <Box sx={{ flex: 1 }}>
          <RecentAccounts accounts={accounts} />
        </Box>

        <Box sx={{ flex: 1 }}>
          {stats?.safety_features && (
            <SafetyFeatures safetyFeatures={stats.safety_features} />
          )}
        </Box>
      </Box>
    </Box>
  );
}
