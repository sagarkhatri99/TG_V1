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
  health_score: number;
  status: string;
  messages_sent_today: number;
  groups_joined_today: number;
  api_calls_today: number;
  flood_wait_count: number;
  spam_error_count: number;
  auth_error_count: number;
  generic_error_count: number;
  is_restricted: boolean;
  restriction_reason?: string;
  restriction_until?: string;
  last_activity: string;
  last_error_time?: string;
  error_history: any[];
}

export default function HealthDashboard() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [healthData, setHealthData] = useState<AccountHealth[]>([]);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    fetchHealthData();
  }, []);

  const fetchHealthData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      const response = await api.get('/api/health/accounts');
      setHealthData(response.data || []);
      setLastUpdated(new Date());
    } catch (error: any) {
      console.error('Failed to fetch health data:', error);
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to load health data' });
      setHealthData([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
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

  const getTotalErrors = (account: AccountHealth) => {
    return account.flood_wait_count + account.spam_error_count +
      account.auth_error_count + account.generic_error_count;
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
              <TableCell>Account</TableCell>
              <TableCell>Health Score</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Today's Activity</TableCell>
              <TableCell>Errors</TableCell>
              <TableCell>Last Activity</TableCell>
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
                      <Typography variant="caption" color="text.secondary">
                        {account.account_phone}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getHealthIcon(account.health_score)}
                      <Box sx={{ width: '100%', maxWidth: 100 }}>
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
                    {account.is_restricted && (
                      <Chip
                        label="Restricted"
                        color="error"
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block">
                      📨 {account.messages_sent_today} messages
                    </Typography>
                    <Typography variant="caption" display="block">
                      📞 {account.api_calls_today} API calls
                    </Typography>
                    <Typography variant="caption" display="block">
                      👥 {account.groups_joined_today} groups joined
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Chip
                        label={`${getTotalErrors(account)} total`}
                        size="small"
                        color={getTotalErrors(account) > 0 ? 'error' : 'default'}
                      />
                      {getTotalErrors(account) > 0 && (
                        <Box sx={{ mt: 1 }}>
                          {account.flood_wait_count > 0 && (
                            <Typography variant="caption" display="block">
                              ⏱️ {account.flood_wait_count} flood wait
                            </Typography>
                          )}
                          {account.spam_error_count > 0 && (
                            <Typography variant="caption" display="block">
                              ⚠️ {account.spam_error_count} spam errors
                            </Typography>
                          )}
                          {account.auth_error_count > 0 && (
                            <Typography variant="caption" display="block">
                              🔐 {account.auth_error_count} auth errors
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {new Date(account.last_activity).toLocaleString()}
                    </Typography>
                    {account.last_error_time && (
                      <Typography variant="caption" display="block" color="error">
                        Last error: {new Date(account.last_error_time).toLocaleString()}
                      </Typography>
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
