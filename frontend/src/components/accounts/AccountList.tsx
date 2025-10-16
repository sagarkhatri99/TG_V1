import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button, CircularProgress, Alert } from '@mui/material';

const AccountList: React.FC = () => {
  const { data, error, isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => axios.get('/api/accounts/list').then(res => res.data.accounts)
  });

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">Error fetching accounts</Alert>;

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Nickname</TableCell>
            <TableCell>Phone Number</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.map((account: any) => (
            <TableRow key={account.id}>
              <TableCell>{account.nickname}</TableCell>
              <TableCell>{account.phone_number}</TableCell>
              <TableCell>{account.status}</TableCell>
              <TableCell>
                <Button>Test</Button>
                <Button>Pause</Button>
                <Button>Resume</Button>
                <Button>Delete</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default AccountList;