import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Button, TextField, Box, Typography, Select, MenuItem, FormControl, InputLabel, CircularProgress, Alert, Checkbox, FormControlLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const PromoForm: React.FC = () => {
  const [accountId, setAccountId] = useState('');
  const [targetGroup, setTargetGroup] = useState('');
  const [promoMessage, setPromoMessage] = useState('');
  const [intervalSeconds, setIntervalSeconds] = useState(3600);
  const [useRandomInterval, setUseRandomInterval] = useState(false);
  const [minInterval, setMinInterval] = useState<number | null>(null);
  const [maxInterval, setMaxInterval] = useState<number | null>(null);

  const navigate = useNavigate();

  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => axios.get('/api/accounts/list').then(res => res.data.accounts)
  });

  const mutation = useMutation({
    mutationFn: (newJob: FormData) => axios.post('/api/autopromo/create-job', newJob),
    onSuccess: () => {
      navigate('/jobs');
    },
  });

  const handleSubmit = () => {
    const formData = new FormData();
    formData.append('account_id', accountId);
    formData.append('target_group', targetGroup);
    formData.append('promo_message', promoMessage);
    formData.append('interval_seconds', intervalSeconds.toString());
    formData.append('use_random_interval', useRandomInterval.toString());
    if (useRandomInterval && minInterval && maxInterval) {
      formData.append('min_interval', minInterval.toString());
      formData.append('max_interval', maxInterval.toString());
    }
    mutation.mutate(formData);
  };

  if (accountsLoading) return <CircularProgress />;

  return (
    <Box>
      <Typography variant="h6">Create Auto Promo Job</Typography>
      <FormControl fullWidth margin="normal">
        <InputLabel>Account</InputLabel>
        <Select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          {accounts?.map((account: any) => (
            <MenuItem key={account.id} value={account.id}>{account.nickname}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField label="Target Group" value={targetGroup} onChange={(e) => setTargetGroup(e.target.value)} fullWidth margin="normal" />
      <TextField label="Promo Message" value={promoMessage} onChange={(e) => setPromoMessage(e.target.value)} fullWidth multiline rows={4} margin="normal" />
      <TextField label="Interval (seconds)" type="number" value={intervalSeconds} onChange={(e) => setIntervalSeconds(parseInt(e.target.value))} fullWidth margin="normal" />
      <FormControlLabel
        control={<Checkbox checked={useRandomInterval} onChange={(e) => setUseRandomInterval(e.target.checked)} />}
        label="Use Random Interval"
      />
      {useRandomInterval && (
        <>
          <TextField label="Min Interval (seconds)" type="number" value={minInterval || ''} onChange={(e) => setMinInterval(parseInt(e.target.value))} fullWidth margin="normal" />
          <TextField label="Max Interval (seconds)" type="number" value={maxInterval || ''} onChange={(e) => setMaxInterval(parseInt(e.target.value))} fullWidth margin="normal" />
        </>
      )}
      <Button onClick={handleSubmit}>Submit</Button>
      {mutation.isError && <Alert severity="error">Error creating job</Alert>}
    </Box>
  );
};

export default PromoForm;