import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  CircularProgress,
} from '@mui/material';

import {
  AccountCircle,
  TrendingUp,
  Security,
  Speed,
  CheckCircle,
  Warning,
  Error,
} from '@mui/icons-material';
import api, { endpoints } from '../api/Index';
import type { SystemStats, TelegramAccount } from '../Types/Index';



export default function Dashboard() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [meStats, setMeStats] = useState<{ active_accounts: number; active_sessions: number } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [loading, setLoading] = useState(true);


  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, accountsResponse, meStatsResponse] = await Promise.all([
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


  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle color="success" />;
      case 'paused': return <Warning color="warning" />;
      case 'error': return <Error color="error" />;
      default: return <Warning color="action" />;
    }
  };


  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'active': return 'success';
      case 'paused': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };


  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
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


      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, flexWrap: 'wrap', gap: 3, mb: 4 }}>
        <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Active Accounts
                  </Typography>
                  <Typography variant="h4">
                    {meStats?.active_accounts ?? accounts.filter(a => a.status === 'active').length}
                  </Typography>
                </Box>
                <AccountCircle color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Active Sessions
                  </Typography>
                  <Typography variant="h4">
                    {meStats?.active_sessions ?? 0}
                  </Typography>
                </Box>
                <TrendingUp color="secondary" />
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Safety Score
                  </Typography>
                  <Typography variant="h4">98%</Typography>
                </Box>
                <Security color="success" />
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    System Status
                  </Typography>
                  <Typography variant="h4">
                    {stats?.system_status || 'Unknown'}
                  </Typography>
                </Box>
                <Speed color={stats?.system_status === 'operational' ? 'success' : 'warning'} />
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Accounts
            </Typography>
            <List>
              {accounts.slice(0, 5).map((account) => (
                <ListItem key={account.id}>
                  <ListItemIcon>
                    {getStatusIcon(account.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={account.nickname}
                    secondary={account.phone_number}
                  />
                  <Chip
                    label={account.status}
                    color={getStatusColor(account.status)}
                    size="small"
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Box>

        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Safety Features
            </Typography>
            <List>
              {stats?.safety_features && Object.entries(stats.safety_features).map(([key, value]) => (
                <ListItem key={key}>
                  <ListItemIcon>
                    <CheckCircle color={value ? 'success' : 'action'} />
                  </ListItemIcon>
                  <ListItemText
                    primary={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    secondary={value ? 'Active' : 'Inactive'}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
