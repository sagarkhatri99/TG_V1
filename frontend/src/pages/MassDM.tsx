import React from 'react';
import { Box, Typography, Grid } from '@mui/material';
import MassDMAccountForm from '../components/mass-dm/MassDMAccountForm';
import MassDMBotForm from '../components/mass-dm/MassDMBotForm';

const MassDM: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Mass DM
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <MassDMAccountForm />
        </Grid>
        <Grid item xs={12} md={6}>
          <MassDMBotForm />
        </Grid>
      </Grid>
    </Box>
  );
};

export default MassDM;