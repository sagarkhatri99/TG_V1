import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Button, TextField, Box, Typography, Select, MenuItem, FormControl, InputLabel, CircularProgress, Alert } from '@mui/material';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';

const MassDMAccountForm: React.FC = () => {
  const [accountId, setAccountId] = useState('');
  const [message, setMessage] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const navigate = useNavigate();

  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => axios.get('/api/accounts/list').then(res => res.data.accounts)
  });

  const mutation = useMutation({
    mutationFn: (newJob: FormData) => axios.post('/api/dm/account/create', newJob),
    onSuccess: () => {
      navigate('/jobs');
    },
  });

  const onDrop = (acceptedFiles: File[]) => {
    setCsvFile(acceptedFiles[0]);
  };

  const { getRootProps, getInputProps } = useDropzone({ onDrop, accept: { 'text/csv': ['.csv'] } });

  const handleSubmit = () => {
    if (!csvFile) return;
    const formData = new FormData();
    formData.append('account_id', accountId);
    formData.append('message', message);
    formData.append('csv_file', csvFile);
    mutation.mutate(formData);
  };

  if (accountsLoading) return <CircularProgress />;

  return (
    <Box>
      <Typography variant="h6">Mass DM (Account Mode)</Typography>
      <FormControl fullWidth margin="normal">
        <InputLabel>Account</InputLabel>
        <Select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          {accounts?.map((account: any) => (
            <MenuItem key={account.id} value={account.id}>{account.nickname}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField label="Message" value={message} onChange={(e) => setMessage(e.target.value)} fullWidth multiline rows={4} margin="normal" />
      <Box {...getRootProps()} sx={{ border: '2px dashed grey', p: 2, mt: 2, textAlign: 'center' }}>
        <input {...getInputProps()} />
        <p>Drag 'n' drop a CSV file here, or click to select one</p>
        {csvFile && <p>{csvFile.name}</p>}
      </Box>
      <Button onClick={handleSubmit} sx={{ mt: 2 }}>Submit</Button>
      {mutation.isError && <Alert severity="error">Error creating job</Alert>}
    </Box>
  );
};

export default MassDMAccountForm;