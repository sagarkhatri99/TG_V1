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
} from '@mui/material';
import { PlayArrow, Pause, Delete, Refresh, Download } from '@mui/icons-material';
import api from '../api/Index';

interface Job {
  id: number;
  telegram_account_id: number;
  job_type: string;
  status: 'pending' | 'running' | 'processing' | 'paused' | 'completed' | 'failed';
  progress: number;
  total_tasks: number;
  created_at: string;
  error_message: string | null;
}

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);

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

  const handleDelete = async (jobId: number) => {
    try {
      await api.delete(`/api/jobs/${jobId}`);
      fetchJobs();
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to delete job.' });
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
            <IconButton onClick={() => { setLoading(true); fetchJobs(); }} disabled={loading}>
              <Refresh />
            </IconButton>
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
                    <TableCell>Status</TableCell>
                    <TableCell>Progress</TableCell>
                    <TableCell>Created At</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell>{job.id}</TableCell>
                      <TableCell>{job.job_type}</TableCell>
                      <TableCell>{getStatusChip(job.status)}</TableCell>
                      <TableCell>{job.progress}%</TableCell>
                      <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                      <TableCell>
                        {job.status === 'running' || job.status === 'processing' ? (
                          <IconButton onClick={() => handlePause(job.id)} size="small">
                            <Pause />
                          </IconButton>
                        ) : job.status === 'paused' ? (
                          <IconButton onClick={() => handleResume(job.id)} size="small">
                            <PlayArrow />
                          </IconButton>
                        ) : null}
                        <IconButton onClick={() => handleDelete(job.id)} size="small" disabled={job.status === 'running'}>
                          <Delete />
                        </IconButton>
                        {job.job_type === 'group_monitor' && job.status === 'completed' && (
                          <IconButton
                            onClick={() => window.open(`/api/group-monitor/download?job_id=${job.id}`, '_blank')}
                            size="small"
                          >
                            <Download />
                          </IconButton>
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
    </Box>
  );
}
