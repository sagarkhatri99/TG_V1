import React from 'react';
import { Box, Typography } from '@mui/material';
import MonitorForm from '../components/monitor/MonitorForm';

const MonitorGroups: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Monitor Groups
      </Typography>
      <MonitorForm />
    </Box>
  );
};

export default MonitorGroups;