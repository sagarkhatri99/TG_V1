import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/Index';
import toast from 'react-hot-toast';

interface CampaignDetail {
  id: number;
  name: string;
  status: string;
  total_targets: number;
  sent_count: number;
  failed_count: number;
  reply_count: number;
  created_at: string;
  start_at?: string;
  end_at?: string;
}

interface Interaction {
  id: number;
  target_user_id: string;
  telegram_first_name?: string;
  current_phase: string;
  status: string;
  last_interaction_at: string;
}

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [jobInfo, setJobInfo] = useState<{ job_id?: number; task_id?: string } | null>(null);

  useEffect(() => {
    if (id) {
      fetchCampaign();
      fetchInteractions();
    }
  }, [id]);

  const fetchCampaign = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/campaigns/${id}`);
      setCampaign(response.data);
    } catch (error: any) {
      console.error('Failed to fetch campaign:', error);
      toast.error(error.response?.data?.detail || 'Failed to fetch campaign');
    } finally {
      setLoading(false);
    }
  };

  const fetchInteractions = async () => {
    try {
      const response = await api.get(`/api/campaigns/${id}/interactions`);
      setInteractions(response.data);
    } catch (error: any) {
      console.error('Failed to fetch interactions:', error);
    }
  };

  const handleStart = async () => {
    try {
      console.log(`Starting campaign ${id}...`);
      const response = await api.post(`/api/campaigns/${id}/start`);
      console.log('Campaign started:', response.data);

      setJobInfo({ job_id: response.data.job_id, task_id: response.data.task_id });
      toast.success(`Campaign started! Job ID: ${response.data.job_id}`);
      fetchCampaign();
    } catch (error: any) {
      console.error('Campaign start failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to start campaign');
    }
  };

  const handlePause = async () => {
    try {
      await api.post(`/api/campaigns/${id}/pause`);
      toast.success('Campaign paused');
      fetchCampaign();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to pause campaign');
    }
  };

  if (loading || !campaign) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
      </Box>
    );
  }

  const progress = campaign.total_targets > 0
    ? (campaign.sent_count / campaign.total_targets) * 100
    : 0;

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<BackIcon />} onClick={() => navigate('/campaigns')} sx={{ mb: 2 }}>
        Back to Campaigns
      </Button>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h4">{campaign.name}</Typography>
                <Chip label={campaign.status} color="primary" />
              </Box>

              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Total Targets
                  </Typography>
                  <Typography variant="h5">{campaign.total_targets}</Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Sent
                  </Typography>
                  <Typography variant="h5" color="success.main">
                    {campaign.sent_count}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Failed
                  </Typography>
                  <Typography variant="h5" color="error.main">
                    {campaign.failed_count}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Replies
                  </Typography>
                  <Typography variant="h5" color="info.main">
                    {campaign.reply_count}
                  </Typography>
                </Grid>
              </Grid>

              {jobInfo && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Job ID:</strong> {jobInfo.job_id}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Task ID:</strong> {jobInfo.task_id}
                  </Typography>
                </Alert>
              )}

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Progress: {progress.toFixed(1)}%
                </Typography>
                <LinearProgress variant="determinate" value={progress} />
              </Box>

              <Box sx={{ display: 'flex', gap: 2 }}>
                {campaign.status === 'draft' || campaign.status === 'paused' ? (
                  <Button
                    variant="contained"
                    startIcon={<PlayIcon />}
                    onClick={handleStart}
                  >
                    {campaign.status === 'draft' ? 'Start Campaign' : 'Resume Campaign'}
                  </Button>
                ) : campaign.status === 'running' ? (
                  <Button
                    variant="outlined"
                    startIcon={<PauseIcon />}
                    onClick={handlePause}
                  >
                    Pause Campaign
                  </Button>
                ) : null}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                User Interactions
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>User ID</TableCell>
                      <TableCell>Name</TableCell>
                      <TableCell>Phase</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Last Interaction</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {interactions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          No interactions yet
                        </TableCell>
                      </TableRow>
                    ) : (
                      interactions.map((interaction) => (
                        <TableRow key={interaction.id}>
                          <TableCell>{interaction.target_user_id}</TableCell>
                          <TableCell>{interaction.telegram_first_name || '-'}</TableCell>
                          <TableCell>{interaction.current_phase}</TableCell>
                          <TableCell>
                            <Chip label={interaction.status} size="small" />
                          </TableCell>
                          <TableCell>
                            {new Date(interaction.last_interaction_at).toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
