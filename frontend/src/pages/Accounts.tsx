import React from 'react';
import { Box, Typography } from '@mui/material';
import AccountList from '../components/accounts/AccountList';
import AddAccountForm from '../components/accounts/AddAccountForm';

const Accounts: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Accounts
      </Typography>
      <AddAccountForm />
      <AccountList />
    </Box>
  );
};

export default Accounts;