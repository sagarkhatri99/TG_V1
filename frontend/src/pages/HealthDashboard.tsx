import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Alert,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import api from '../api/Index';
import toast from 'react-hot-toast';

interface HealthCheck {
  status: string;
  checks: {
    redis?: string | { status: string; error: string };
    db?: string | { status: string; error: string };
    celery_broker?: string | { status: string; error: string };
    workers?: {
      status: string;
      active_workers?: string[];
      has_campaign_worker?: boolean;
    };
  };
}

export default function HealthDashboard() {
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/health/diagnose');
      setHealth(response.data);
      console.log('Health check:', response.data);
    } catch (error: any) {
      console.error('Health check failed:', error);
      toast.error('Failed to fetch health status');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'unhealthy':
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const renderCheckValue = (value: any) => {
    if (typeof value === 'string') {
      return <Chip label={value} color={getStatusColor(value)} size="small" />;
    }
    if (typeof value === 'object' && value.status) {
      return (
        <Box>
          <Chip label={value.status} color={getStatusColor(value.status)} size="small" />
          {value.error && (
            <Typography variant="caption" color="error" display="block" sx={{ mt: 1 }}>
              {value.error}
            </Typography>
          )}
        </Box>
      );
    }
    return JSON.stringify(value);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">System Health</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={checkHealth}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {health && (
        <Alert severity={getStatusColor(health.status) as any} sx={{ mb: 3 }}>
          System Status: <strong>{health.status.toUpperCase()}</strong>
        </Alert>
      )}

      <Grid container spacing={3}>
        {health?.checks && Object.entries(health.checks).map(([key, value]) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={key}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {key.replace(/_/g, ' ').toUpperCase()}
                </Typography>
                {typeof value === 'object' && 'active_workers' in value ? (
                  <Box>
                    <Chip
                      label={value.status || 'unknown'}
                      color={getStatusColor(value.status || 'unknown')}
                      size="small"
                      sx={{ mb: 1 }}
                    />
                    {value.active_workers && value.active_workers.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Active Workers:
                        </Typography>
                        {value.active_workers.map((worker, idx) => (
                          <Typography key={idx} variant="body2">
                            • {worker}
                          </Typography>
                        ))}
                      </Box>
                    )}
                    {value.has_campaign_worker !== undefined && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Campaign Worker:{' '}
                        <Chip
                          label={value.has_campaign_worker ? 'Active' : 'Inactive'}
                          color={value.has_campaign_worker ? 'success' : 'error'}
                          size="small"
                        />
                      </Typography>
                    )}
                  </Box>
                ) : (
                  renderCheckValue(value)
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
