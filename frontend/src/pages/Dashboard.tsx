import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, Paper, Chip } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const Dashboard: React.FC = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => axios.get('/api/jobs/reports').then(res => res.data.summary)
  });
  const { user } = useAuth();
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    if (user?.status === 'trial' && user.trial_end_date) {
      const interval = setInterval(() => {
        const now = new Date();
        const endDate = new Date(user.trial_end_date);
        const diff = endDate.getTime() - now.getTime();

        if (diff <= 0) {
          setTimeLeft('Trial expired');
          clearInterval(interval);
          return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        setTimeLeft(`${days}d ${hours}h ${minutes}m left`);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [user]);

  if (isLoading) return <p>Loading...</p>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Chip label={`Subscription: ${user?.subscription_plan}`} color="primary" sx={{ mb: 2 }} />
      {user?.status === 'trial' && <Chip label={`Trial ends in: ${timeLeft}`} color="secondary" sx={{ mb: 2, ml: 1 }} />}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Total Jobs</Typography>
            <Typography variant="h4">{stats?.total_jobs}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Completion Rate</Typography>
            <Typography variant="h4">{stats?.completion_rate}%</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Total Messages Sent</Typography>
            <Typography variant="h4">{stats?.total_messages_sent}</Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;