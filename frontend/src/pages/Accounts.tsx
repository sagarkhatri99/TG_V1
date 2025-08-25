import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Science as TestIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import api, { endpoints } from '../api';
import type { TelegramAccount, CreateAccountRequest } from '../types';

export default function Accounts() {
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<TelegramAccount | null>(null);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  const [createForm, setCreateForm] = useState<CreateAccountRequest>({
    api_id: 0,
    api_hash: '',
    phone_number: '',
    nickname: '',
  });
  const [otpCode, setOtpCode] = useState('');

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await api.get(endpoints.accounts.list);
      setAccounts(response.data.accounts || []);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to fetch accounts' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAccount = async () => {
    try {
      const formData = new FormData();
      Object.entries(createForm).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });

      const response = await api.post(endpoints.accounts.create, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setAlert({ type: 'success', message: 'Account created. Please verify with OTP.' });
      setCreateDialogOpen(false);
      
      // Send verification code
      await api.post(endpoints.accounts.sendCode(response.data.account_id));
      
      // Show verify dialog
      setSelectedAccount({ 
        ...createForm, 
        id: response.data.account_id, 
        status: 'pending_verification', 
        trust_score: 0, 
        risk_score: 0, 
        last_activity: '', 
        daily_message_count: 0, 
        created_at: new Date().toISOString() 
      });
      setVerifyDialogOpen(true);
      
      fetchAccounts();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create account' });
    }
  };

  const handleVerifyAccount = async () => {
    if (!selectedAccount) return;

    try {
      const formData = new FormData();
      formData.append('otp_code', otpCode);

      await api.post(endpoints.accounts.verify(selectedAccount.id), formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setAlert({ type: 'success', message: 'Account verified successfully!' });
      setVerifyDialogOpen(false);
      setOtpCode('');
      fetchAccounts();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Verification failed' });
    }
  };

  const handlePauseResume = async (account: TelegramAccount) => {
    try {
      const endpoint = account.status === 'active' 
        ? endpoints.accounts.pause(account.id)
        : endpoints.accounts.resume(account.id);
      
      await api.post(endpoint);
      setAlert({ 
        type: 'success', 
        message: `Account ${account.status === 'active' ? 'paused' : 'resumed'} successfully` 
      });
      fetchAccounts();
    } catch (error) {
      setAlert({ type: 'error', message: 'Operation failed' });
    }
  };

  const handleTestConnection = async (account: TelegramAccount) => {
    try {
      const response = await api.post(endpoints.accounts.test(account.id));
      setAlert({ 
        type: 'success', 
        message: `Connection test successful. User: ${response.data.first_name}` 
      });
    } catch (error) {
      setAlert({ type: 'error', message: 'Connection test failed' });
    }
  };

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'active': return 'success';
      case 'paused': return 'warning';
      case 'error': return 'error';
      case 'pending_verification': return 'info';
      default: return 'default';
    }
  };

  const getRiskColor = (risk: number): any => {
    if (risk < 0.3) return 'success';
    if (risk < 0.7) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Accounts Management</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Add Account
        </Button>
      </Box>

      {alert && (
        <Alert 
          severity={alert.type} 
          onClose={() => setAlert(null)}
          sx={{ mb: 2 }}
        >
          {alert.message}
        </Alert>
      )}

      <Card>
        <CardContent>
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Account</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Trust Score</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Messages Today</TableCell>
                  <TableCell>Last Activity</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell>
                      <Typography variant="subtitle2">{account.nickname}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        ID: {account.id}
                      </Typography>
                    </TableCell>
                    <TableCell>{account.phone_number}</TableCell>
                    <TableCell>
                      <Chip 
                        label={account.status}
                        color={getStatusColor(account.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={account.trust_score}
                        color="primary"
                        variant="outlined"
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={account.risk_score.toFixed(2)}
                        color={getRiskColor(account.risk_score)}
                        variant="outlined"
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{account.daily_message_count}</TableCell>
                    <TableCell>
                      {account.last_activity ? 
                        format(new Date(account.last_activity), 'MMM dd, HH:mm') : 
                        'Never'
                      }
                    </TableCell>
                    <TableCell>
                      <Box display="flex" gap={1}>
                        <Tooltip title="Test Connection">
                          <IconButton 
                            size="small" 
                            onClick={() => handleTestConnection(account)}
                            disabled={account.status !== 'active'}
                          >
                            <TestIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={account.status === 'active' ? 'Pause' : 'Resume'}>
                          <IconButton 
                            size="small" 
                            onClick={() => handlePauseResume(account)}
                            disabled={account.status === 'pending_verification'}
                          >
                            {account.status === 'active' ? <PauseIcon /> : <PlayIcon />}
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Create Account Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Telegram Account</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="API ID"
                  type="number"
                  value={createForm.api_id || ''}
                  onChange={(e) => setCreateForm({ ...createForm, api_id: parseInt(e.target.value) || 0 })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="API Hash"
                  value={createForm.api_hash}
                  onChange={(e) => setCreateForm({ ...createForm, api_hash: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  placeholder="+1234567890"
                  value={createForm.phone_number}
                  onChange={(e) => setCreateForm({ ...createForm, phone_number: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Nickname"
                  value={createForm.nickname}
                  onChange={(e) => setCreateForm({ ...createForm, nickname: e.target.value })}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateAccount} variant="contained">Create Account</Button>
        </DialogActions>
      </Dialog>

      {/* Verify Account Dialog */}
      <Dialog open={verifyDialogOpen} onClose={() => setVerifyDialogOpen(false)}>
        <DialogTitle>Verify Account</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Enter the OTP code sent to {selectedAccount?.phone_number}
          </Typography>
          <TextField
            fullWidth
            label="OTP Code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVerifyDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleVerifyAccount} variant="contained">Verify</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
