import React from 'react';
import { Box, Typography } from '@mui/material';
import PromoForm from '../components/auto-promo/PromoForm';

const AutoPromo: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Auto Promo
      </Typography>
      <PromoForm />
    </Box>
  );
};

export default AutoPromo;