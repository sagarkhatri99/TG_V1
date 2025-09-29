import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
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
  LinearProgress,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';

interface JobReportsDialogProps {
  open: boolean;
  onClose: () => void;
  reports: any;
}

const JobReportsDialog: React.FC<JobReportsDialogProps> = ({ open, onClose, reports }) => {
  if (!reports) return null;

  const { summary, status_breakdown, job_type_breakdown, recent_completed_jobs } = reports;

  const getStatusColor = (status: string) => {
    const colorMap: { [key: string]: 'success' | 'warning' | 'error' | 'info' | 'default' } = {
      completed: 'success',
      running: 'info',
      pending: 'warning',
      paused: 'default',
      failed: 'error',
    };
    return colorMap[status] || 'default';
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AssessmentIcon />
          Job Reports & Analytics
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {/* Summary Cards */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)', md: '1 1 calc(25% - 12px)' } }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AssessmentIcon color="primary" />
                  <Box>
                    <Typography variant="h6">{summary.total_jobs}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Jobs
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>

          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)', md: '1 1 calc(25% - 12px)' } }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrendingUpIcon color="success" />
                  <Box>
                    <Typography variant="h6">{summary.completion_rate}%</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Completion Rate
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>

          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)', md: '1 1 calc(25% - 12px)' } }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ScheduleIcon color="info" />
                  <Box>
                    <Typography variant="h6">{summary.jobs_last_30_days}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Last 30 Days
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>

          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)', md: '1 1 calc(25% - 12px)' } }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircleIcon color="success" />
                  <Box>
                    <Typography variant="h6">{summary.total_messages_sent}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Messages Sent
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {/* Status Breakdown */}
          <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 12px)' } }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Jobs by Status
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {Object.entries(status_breakdown).map(([status, count]) => (
                    <Box key={status} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Chip 
                        label={status} 
                        color={getStatusColor(status)} 
                        size="small"
                        sx={{ minWidth: 80 }}
                      />
                      <Typography variant="body2">{count as number}</Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Box>

          {/* Job Type Breakdown */}
          <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 12px)' } }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Jobs by Type
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {job_type_breakdown.map((type: any, index: number) => (
                    <Box key={index}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Typography variant="body2" fontWeight="bold">
                          {type.job_type.replace('_', ' ').toUpperCase()}
                        </Typography>
                        <Typography variant="body2">
                          {type.count} jobs ({type.avg_completion}% avg)
                        </Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={Math.max(0, Math.min(100, type.avg_completion))} 
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Box>

          {/* Recent Completed Jobs */}
          <Box sx={{ flex: '1 1 100%' }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Completed Jobs
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>ID</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Completion</TableCell>
                        <TableCell>Messages</TableCell>
                        <TableCell>Duration</TableCell>
                        <TableCell>Completed</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recent_completed_jobs.map((job: any) => (
                        <TableRow key={job.id}>
                          <TableCell>{job.id}</TableCell>
                          <TableCell>{job.job_type}</TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 150 }}>
                              {job.user_description || 'No description'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={Math.max(0, Math.min(100, job.completion_percentage))} 
                                sx={{ width: 60, height: 6 }}
                              />
                              <Typography variant="body2">
                                {Math.max(0, Math.min(100, job.completion_percentage)).toFixed(1)}%
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {job.messages_sent} / {job.messages_planned}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {job.duration_hours ? `${job.duration_hours}h` : 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(job.completed_at).toLocaleDateString()}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default JobReportsDialog;