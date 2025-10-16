import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Button, TextField, Box, Typography, Select, MenuItem, FormControl, InputLabel, CircularProgress, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const MonitorForm: React.FC = () => {
  const [accountId, setAccountId] = useState('');
  const [groups, setGroups] = useState('');
  const [keywords, setKeywords] = useState('');
  const [users, setUsers] = useState('');
  const [limit, setLimit] = useState(100);

  const navigate = useNavigate();

  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => axios.get('/api/accounts/list').then(res => res.data.accounts)
  });

  const mutation = useMutation({
    mutationFn: (newJob: any) => axios.post('/api/monitor/create', newJob),
    onSuccess: () => {
      navigate('/jobs');
    },
  });

  const handleSubmit = () => {
    const formData = new FormData();
    formData.append('account_id', accountId);
    formData.append('groups', groups);
    formData.append('keywords', keywords);
    formData.append('users', users);
    formData.append('limit', limit.toString());
    mutation.mutate(formData);
  };

  if (accountsLoading) return <CircularProgress />;

  return (
    <Box>
      <Typography variant="h6">Create Monitor Job</Typography>
      <FormControl fullWidth margin="normal">
        <InputLabel>Account</InputLabel>
        <Select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          {accounts?.map((account: any) => (
            <MenuItem key={account.id} value={account.id}>{account.nickname}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField label="Groups (comma-separated)" value={groups} onChange={(e) => setGroups(e.target.value)} fullWidth margin="normal" />
      <TextField label="Keywords (comma-separated)" value={keywords} onChange={(e) => setKeywords(e.target.value)} fullWidth margin="normal" />
      <TextField label="Users (comma-separated)" value={users} onChange={(e) => setUsers(e.target.value)} fullWidth margin="normal" />
      <TextField label="Limit" type="number" value={limit} onChange={(e) => setLimit(parseInt(e.target.value))} fullWidth margin="normal" />
      <Button onClick={handleSubmit}>Submit</Button>
      {mutation.isError && <Alert severity="error">Error creating job</Alert>}
    </Box>
  );
};

export default MonitorForm;