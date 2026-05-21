import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
} from '@mui/material';
import {
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import api from '../api/Index';

interface AccountHealth {
  id: number;
  account_id: number;
  account_nickname: string;
  account_phone: string;
  trust_tier: string;
  warmup_stage: string;
  health_score: number;
  status: string;
  messages_sent_hour: number;
  messages_sent_today: number;
  enforced_min_delay: number;
  enforced_max_delay: number;
  active_job_id?: number;
  active_job_type?: string;
  lock_holder?: string;
  latest_error_summary: string;
  recommendation_reason: string;
  api_calls_today: number;
  flood_wait_count: number;
  is_restricted: boolean;
  last_activity: string;
}

export default function HealthDashboard() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [healthData, setHealthData] = useState<AccountHealth[]>([]);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealthData = useCallback(async (silent = false, signal?: AbortSignal) => {
    if (refreshing) return;
    try {
      if (!silent) setLoading(true);
      setRefreshing(true);
      const response = await api.get('/api/health/accounts', { signal });
      setHealthData(response.data || []);
      setLastUpdated(new Date());
    } catch (error: any) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') return;
      console.error('Failed to fetch health data:', error);
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to load health data' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [refreshing]);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealthData(false, controller.signal);

    const intervalId = setInterval(() => {
      fetchHealthData(true, controller.signal);
    }, 20000); // 20 second polling

    return () => {
      clearInterval(intervalId);
      controller.abort();
    };
  }, []);

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
  };

  const getHealthIcon = (score: number) => {
    if (score >= 80) return <HealthyIcon color="success" />;
    if (score >= 50) return <WarningIcon color="warning" />;
    return <ErrorIcon color="error" />;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'restricted': return 'error';
      case 'banned': return 'error';
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
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h4">Account Health Dashboard</Typography>
        <Box display="flex" alignItems="center" gap={1}>
          {lastUpdated && (
            <Typography variant="caption" color="text.secondary">
              Updated {lastUpdated.toLocaleTimeString()}
            </Typography>
          )}
          <Button
            variant="outlined"
            startIcon={refreshing || loading ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={() => fetchHealthData(false)}
            disabled={refreshing || loading}
          >
            Refresh
          </Button>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
        Monitor account health scores, API usage, and error rates.
      </Typography>

      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
          {alert.message}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Accounts
              </Typography>
              <Typography variant="h4">{healthData.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Healthy Accounts
              </Typography>
              <Typography variant="h4" color="success.main">
                {healthData.filter((a: AccountHealth) => a.health_score >= 80).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Warning Status
              </Typography>
              <Typography variant="h4" color="warning.main">
                {healthData.filter((a: AccountHealth) => a.health_score >= 50 && a.health_score < 80).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Critical Status
              </Typography>
              <Typography variant="h4" color="error.main">
                {healthData.filter((a: AccountHealth) => a.health_score < 50).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Account Health Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Account / Tier</TableCell>
              <TableCell>Health Score</TableCell>
              <TableCell>Status / Job</TableCell>
              <TableCell>Throughput (Hour/24h)</TableCell>
              <TableCell>Protection / Delays</TableCell>
              <TableCell>Recommendation</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {healthData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No accounts found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              healthData.map((account: AccountHealth) => (
                <TableRow key={account.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {account.account_nickname}
                      </Typography>
                      <Chip 
                        label={account.trust_tier.toUpperCase()} 
                        size="small" 
                        variant="outlined" 
                        sx={{ mt: 0.5, fontSize: '0.65rem', height: 20 }}
                      />
                      <Typography variant="caption" color="text.secondary" display="block">
                        {account.account_phone}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getHealthIcon(account.health_score)}
                      <Box sx={{ width: '100%', maxWidth: 80 }}>
                        <LinearProgress
                          variant="determinate"
                          value={account.health_score}
                          color={getHealthColor(account.health_score)}
                        />
                        <Typography variant="caption">{account.health_score.toFixed(0)}%</Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={account.status}
                      color={getStatusColor(account.status)}
                      size="small"
                    />
                    {account.active_job_id && (
                      <Box sx={{ mt: 1 }}>
                        <Chip 
                          label={`Job #${account.active_job_id} (${account.active_job_type})`} 
                          size="small" 
                          color="primary"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      </Box>
                    )}
                    {account.lock_holder && (
                       <Typography variant="caption" display="block" sx={{ color: 'warning.main', mt: 0.5 }}>
                         🔒 Locked by Worker
                       </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      <strong>{account.messages_sent_hour}</strong> / hr
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {account.messages_sent_today} in 24h
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block">
                      ⏱️ {account.enforced_min_delay}s - {account.enforced_max_delay}s
                    </Typography>
                    {account.flood_wait_count > 0 && (
                      <Typography variant="caption" display="block" color="error">
                        ⚠️ {account.flood_wait_count} Floods
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      {account.recommendation_reason}
                    </Typography>
                    {account.latest_error_summary && (
                      <Alert severity="error" icon={false} sx={{ py: 0, mt: 0.5, fontSize: '0.7rem' }}>
                        {account.latest_error_summary.substring(0, 50)}...
                      </Alert>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
