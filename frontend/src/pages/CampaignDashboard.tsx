import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material';
import { Add as AddIcon, PlayArrow as PlayIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../api/Index';
import toast from 'react-hot-toast';

interface Campaign {
  id: number;
  name: string;
  status: string;
  total_targets: number;
  sent_count: number;
  failed_count: number;
  reply_count: number;
  created_at: string;
}

export default function CampaignDashboard() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/campaigns/');
      setCampaigns(response.data || []);
    } catch (error: any) {
      console.error('Failed to fetch campaigns:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to fetch campaigns';
      setError(errorMsg);
      toast.error(errorMsg);
      // Set empty array to prevent undefined errors
      setCampaigns([]);
    } finally {
      setLoading(false);
    }
  };

  const handleStartCampaign = async (campaignId: number) => {
    try {
      console.log(`Starting campaign ${campaignId}...`);
      const response = await api.post(`/api/campaigns/${campaignId}/start`);
      console.log('Campaign started:', response.data);

      toast.success(`Campaign started! Job ID: ${response.data.job_id}`);
      fetchCampaigns();
    } catch (error: any) {
      console.error('Campaign start failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to start campaign');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'paused':
        return 'warning';
      case 'completed':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Campaigns</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/campaigns/new')}
        >
          Create Campaign
        </Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {campaigns.length === 0 ? (
          <Grid size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography align="center" color="text.secondary">
                  No campaigns yet. Create your first campaign to get started!
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ) : (
          campaigns.map((campaign) => (
            <Grid size={{ xs: 12, md: 6, lg: 4 }} key={campaign.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6">{campaign.name}</Typography>
                    <Chip
                      label={campaign.status}
                      color={getStatusColor(campaign.status)}
                      size="small"
                    />
                  </Box>

                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Targets: {campaign.total_targets}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Sent: {campaign.sent_count} | Failed: {campaign.failed_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Replies: {campaign.reply_count}
                  </Typography>

                  {campaign.total_targets > 0 && (
                    <LinearProgress
                      variant="determinate"
                      value={(campaign.sent_count / campaign.total_targets) * 100}
                      sx={{ my: 2 }}
                    />
                  )}

                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => navigate(`/campaigns/${campaign.id}`)}
                    >
                      View Details
                    </Button>
                    {campaign.status !== 'running' && (
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<PlayIcon />}
                        onClick={() => handleStartCampaign(campaign.id)}
                      >
                        Start
                      </Button>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))
        )}
      </Grid>
    </Box>
  );
}
