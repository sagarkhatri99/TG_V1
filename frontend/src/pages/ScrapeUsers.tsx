import React from 'react';
import { Box, Typography } from '@mui/material';
import ScrapeStepper from '../components/scrape-users/ScrapeStepper';

const ScrapeUsers: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Scrape Users
      </Typography>
      <ScrapeStepper />
    </Box>
  );
};

export default ScrapeUsers;