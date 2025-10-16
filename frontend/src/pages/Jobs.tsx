import React from 'react';
import { Box, Typography } from '@mui/material';
import JobList from '../components/jobs/JobList';

const Jobs: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Jobs
      </Typography>
      <JobList />
    </Box>
  );
};

export default Jobs;