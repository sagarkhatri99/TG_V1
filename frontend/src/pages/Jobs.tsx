import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Button,
  Tooltip,
} from '@mui/material';
import { PlayArrow, Pause, Delete, Refresh, Download, RestartAlt, Analytics } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import type { AxiosResponse } from 'axios';
import api from '../api/Index';
import JobReportsDialog from '../components/JobReportsDialog';

interface Job {
  id: number;
  telegram_account_id: number;
  job_type: string;
  status: 'pending' | 'running' | 'processing' | 'paused' | 'completed' | 'failed';
  progress: number;
  total_tasks: number;
  created_at: string;
  error_message: string | null;
  user_description: string | null;
  messages_sent: number;
  messages_planned: number;
  completion_percentage: number;
}

export default function Jobs() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [showReports, setShowReports] = useState(false);
  const [reports, setReports] = useState<any>(null);
  const [reportsLoading, setReportsLoading] = useState(false);

  const fetchJobs = async () => {
    try {
      const response = await api.get('/api/jobs/list');
      setJobs(response.data.jobs);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to fetch jobs.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handlePause = async (jobId: number) => {
    try {
      await api.post(`/api/jobs/${jobId}/pause`);
      fetchJobs();
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to pause job.' });
    }
  };

  const handleResume = async (jobId: number) => {
    try {
      await api.post(`/api/jobs/${jobId}/resume`);
      fetchJobs();
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to resume job.' });
    }
  };

  const handleRestart = async (jobId: number) => {
    try {
      await api.post(`/api/jobs/${jobId}/restart`);
      setAlert({ type: 'success', message: 'Job restarted successfully.' });
      fetchJobs();
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Failed to restart job.';
      setAlert({ type: 'error', message });
    }
  };

  const handleDelete = async (jobId: number) => {
    if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
      return;
    }
    try {
      await api.delete(`/api/jobs/${jobId}`);
      setAlert({ type: 'success', message: 'Job deleted successfully.' });
      fetchJobs();
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to delete job.' });
    }
  };

  const fetchReports = async () => {
    setReportsLoading(true);
    try {
      const response = await api.get('/api/jobs/reports');
      setReports(response.data);
      setShowReports(true);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to fetch job reports.' });
    } finally {
      setReportsLoading(false);
    }
  };

  const handleDownloadReports = async () => {
    try {
      const response: AxiosResponse<Blob> = await api.get('/api/jobs/reports/download', {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      // Extract filename from header or use default
      const dispo = (response.headers['content-disposition'] || '') as string;
      const match = dispo.match(/filename="?([^\";]+)"?/i);
      const filename = match ? match[1] : `job_reports_${new Date().toISOString().split('T')[0]}.csv`;

      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setAlert({ type: 'success', message: 'Job reports downloaded successfully!' });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to download job reports' });
    }
  };

  const handleDownload = async (jobId: number, jobType: string) => {
    try {
      const endpoint = jobType === 'group_monitor' ? '/api/group-monitor/download' : '/api/scrape-users/download';
      const response: AxiosResponse<Blob> = await api.get(endpoint, {
        params: { job_id: jobId },
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      // Try to infer filename from header
      const dispo = (response.headers['content-disposition'] || '') as string;
      const match = dispo.match(/filename="?([^";]+)"?/i);
      const defaultFilename = jobType === 'group_monitor' ? `monitored_messages_job_${jobId}.csv` : `scraped_users_job_${jobId}.csv`;
      const filename = match ? match[1] : defaultFilename;

      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      const status = error?.response?.status;
      const serverMsg = error?.response?.data?.detail;
      const message = status === 404 ? 'Results not ready yet. Please try again later.' : (serverMsg || 'Failed to download results.');
      setAlert({ type: 'error', message });
    }
  };

  const getStatusChip = (status: Job['status']) => {
    const colorMap = {
      pending: 'warning',
      processing: 'info',
      running: 'primary',
      paused: 'default',
      completed: 'success',
      failed: 'error',
    };
    return <Chip label={status} color={colorMap[status] as any} />;
  };

  const getTypeChip = (type: string) => {
    const colorMap: any = {
      scrape_users: 'info',
      group_monitor: 'secondary',
      campaign: 'success',
      mass_dm_account: 'primary',
      mass_dm_bot: 'primary'
    };
    return <Chip label={type.replace('_', ' ').toUpperCase()} size="small" variant="outlined" color={colorMap[type] || 'default'} />;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Job Management
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        View and manage all your running, pending, and completed jobs.
      </Typography>

      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ my: 2 }}>
          {alert.message}
        </Alert>
      )}

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Job List</Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                startIcon={<Analytics />}
                onClick={fetchReports}
                disabled={reportsLoading}
              >
                {reportsLoading ? <CircularProgress size={20} /> : 'View Reports'}
              </Button>
              <Button
                variant="contained"
                startIcon={<Download />}
                onClick={handleDownloadReports}
              >
                Download CSV
              </Button>
              <IconButton onClick={() => { setLoading(true); fetchJobs(); }} disabled={loading}>
                <Refresh />
              </IconButton>
            </Box>
          </Box>
          {loading && jobs.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Progress</TableCell>
                    <TableCell>Messages</TableCell>
                    <TableCell>Created At</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell>{job.id}</TableCell>
                      <TableCell>{getTypeChip(job.job_type)}</TableCell>
                      <TableCell>
                        <Typography variant="body2" title={job.user_description || 'No description'}>
                          {job.user_description ? (job.user_description.length > 50 ?
                            `${job.user_description.substring(0, 50)}...` :
                            job.user_description) :
                            'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell>{getStatusChip(job.status)}</TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {(() => {
                            const pct = (job.completion_percentage && job.completion_percentage > 0)
                              ? job.completion_percentage
                              : job.progress;
                            const clamped = Math.max(0, Math.min(100, pct));
                            return `${clamped.toFixed ? clamped.toFixed(1) : clamped}%`;
                          })()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {job.messages_sent || 0} / {job.messages_planned || job.total_tasks || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                      <TableCell>
                        {job.status === 'running' || job.status === 'processing' ? (
                          <IconButton onClick={() => handlePause(job.id)} size="small">
                            <Pause />
                          </IconButton>
                        ) : job.status === 'paused' ? (
                          <>
                            <IconButton onClick={() => handleResume(job.id)} size="small" title="Resume">
                              <PlayArrow />
                            </IconButton>
                            <IconButton onClick={() => handleRestart(job.id)} size="small" color="primary" title="Restart">
                              <RestartAlt />
                            </IconButton>
                          </>
                        ) : null}
                        {(job.status === 'completed' || job.status === 'failed') && (
                          <IconButton onClick={() => handleRestart(job.id)} size="small" color="primary" title="Restart">
                            <RestartAlt />
                          </IconButton>
                        )}
                        <IconButton onClick={() => handleDelete(job.id)} size="small" disabled={job.status === 'running'} color="error">
                          <Delete />
                        </IconButton>
                        {(job.job_type === 'group_monitor' || job.job_type === 'scrape_users') && (
                          <IconButton
                            onClick={() => handleDownload(job.id, job.job_type)}
                            size="small"
                            title="Download results"
                          >
                            <Download />
                          </IconButton>
                        )}
                        {job.job_type === 'campaign' && (
                          <Tooltip title="View Campaign">
                            <IconButton
                              size="small"
                              onClick={() => {
                                const config = JSON.parse((job as any).config || '{}');
                                if (config.campaign_id) {
                                  navigate(`/campaigndashboard?id=${config.campaign_id}`);
                                } else {
                                  navigate('/campaigndashboard');
                                }
                              }}
                            >
                              <Analytics />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <JobReportsDialog
        open={showReports}
        onClose={() => setShowReports(false)}
        reports={reports}
      />
    </Box>
  );
}
