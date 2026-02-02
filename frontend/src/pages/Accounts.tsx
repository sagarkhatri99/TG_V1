import { useState, useEffect } from 'react';
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
  Alert,
  CircularProgress,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Science as TestIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Settings as CampaignIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import api, { endpoints } from '../api/Index';
import type { TelegramAccount, CreateAccountRequest, Proxy, AccountOperatingHours } from '../Types/Index';
import { ImportSessionsDialog } from '../components/accounts/ImportSessionsDialog';

export default function Accounts() {
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [editProxyDialogOpen, setEditProxyDialogOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<TelegramAccount | null>(null);
  const [selectedProxyId, setSelectedProxyId] = useState<number | ''>('');
  const [campaignSettingsDialogOpen, setCampaignSettingsDialogOpen] = useState(false);
  const [operatingHours, setOperatingHours] = useState<AccountOperatingHours>({
    sleep_hour_start: 0,
    sleep_hour_end: 7,
    daily_message_limit: 50
  });
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [loadingActions, setLoadingActions] = useState<{ [key: number]: string }>({});

  const [createForm, setCreateForm] = useState<Omit<CreateAccountRequest, 'proxy_id'> & { proxy_id: number | '' }>({
    api_id: '',
    api_hash: '',
    phone_number: '',
    nickname: '',
    proxy_id: '',
  });
  const [otpCode, setOtpCode] = useState('');


  useEffect(() => {
    fetchAccounts();
    fetchProxies();
  }, []);

  const fetchProxies = async () => {
    try {
      const response = await api.get('/api/proxies/list');
      setProxies(response.data);
    } catch (error) {
      console.error('Failed to fetch proxies', error);
    }
  };


  const fetchAccounts = async () => {
    try {
      const response = await api.get('/api/accounts/list');
      setAccounts(response.data || []);
    } catch (error: any) {
      console.error('Failed to fetch accounts:', error);
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to fetch accounts' });
      setAccounts([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };


  const handleCreateAccount = async () => {
    try {
      const formData = new FormData();
      Object.entries(createForm).forEach(([key, value]) => {
        formData.append(key, (value as any).toString());
      });


      const response = await api.post('/api/accounts/create', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });


      setAlert({ type: 'success', message: 'Account created. Please verify with OTP.' });
      setCreateDialogOpen(false);

      // Send verification code
      await api.post(`/api/accounts/${response.data.account_id}/send-code`);

      // Show verify dialog
      setSelectedAccount({
        id: response.data.account_id,
        phone_number: createForm.phone_number,
        nickname: createForm.nickname,
        proxy_id: createForm.proxy_id ? Number(createForm.proxy_id) : undefined,
        status: 'pending_verification',
        trust_score: 0,
        risk_score: 0,
        last_activity: new Date().toISOString(),
        daily_message_count: 0,
        created_at: new Date().toISOString(),
        sleep_hour_start: undefined,
        sleep_hour_end: undefined,
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
    const actionType = account.status === 'active' ? 'pause' : 'resume';
    setLoadingActions(prev => ({ ...prev, [account.id]: actionType }));

    try {
      const endpoint = account.status === 'active'
        ? endpoints.accounts.pause(account.id)
        : endpoints.accounts.resume(account.id);

      const response = await api.post(endpoint);

      if (actionType === 'resume') {
        // Handle resume with connection test results
        const data = response.data;
        if (data.connection_test === 'passed') {
          setAlert({
            type: 'success',
            message: `Account resumed successfully. Connection test passed. User: ${data.user_info?.first_name || 'Unknown'}`
          });
        } else {
          setAlert({
            type: 'error',
            message: 'Account resume failed: Connection test failed'
          });
        }
      } else {
        setAlert({
          type: 'success',
          message: `Account paused successfully`
        });
      }

      fetchAccounts();
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Operation failed';
      setAlert({ type: 'error', message });
    } finally {
      setLoadingActions(prev => {
        const newState = { ...prev };
        delete newState[account.id];
        return newState;
      });
    }
  };


  const handleTestConnection = async (account: TelegramAccount) => {
    setLoadingActions(prev => ({ ...prev, [account.id]: 'test' }));

    try {
      const response = await api.post(endpoints.accounts.test(account.id));
      setAlert({
        type: 'success',
        message: `Connection test successful. User: ${response.data.first_name || response.data.username || 'Unknown'}`
      });
      fetchAccounts();
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Connection test failed';
      setAlert({ type: 'error', message });
      fetchAccounts(); // Refresh to show updated status if account status changed
    } finally {
      setLoadingActions(prev => {
        const newState = { ...prev };
        delete newState[account.id];
        return newState;
      });
    }
  };

  const handleDeleteAccount = async (account: TelegramAccount) => {
    if (!confirm(`Are you sure you want to delete the account "${account.nickname}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(endpoints.accounts.delete(account.id));
      setAlert({
        type: 'success',
        message: `Account "${account.nickname}" deleted successfully`
      });
      fetchAccounts();
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to delete account'
      });
    }
  };

  const handleOpenEditProxy = (account: TelegramAccount) => {
    setSelectedAccount(account);
    setSelectedProxyId(account.proxy?.id || '');
    setEditProxyDialogOpen(true);
  };

  const handleUpdateProxy = async () => {
    if (!selectedAccount) return;

    try {
      await api.patch(`/api/accounts/${selectedAccount.id}`, {
        proxy_id: selectedProxyId === '' ? null : selectedProxyId
      });
      setAlert({
        type: 'success',
        message: 'Proxy updated successfully!'
      });
      setEditProxyDialogOpen(false);
      fetchAccounts();
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to update proxy'
      });
    }
  };

  const handleOpenCampaignSettings = (account: TelegramAccount) => {
    setSelectedAccount(account);
    setOperatingHours({
      sleep_hour_start: account.sleep_hour_start || 0,
      sleep_hour_end: account.sleep_hour_end || 7,
      daily_message_limit: account.daily_message_limit || 50
    });
    setCampaignSettingsDialogOpen(true);
  };

  const handleUpdateCampaignSettings = async () => {
    if (!selectedAccount) return;

    try {
      await api.patch(`/api/accounts/${selectedAccount.id}/operating-hours`, operatingHours);
      setAlert({ type: 'success', message: 'Account operating hours updated successfully!' });
      setCampaignSettingsDialogOpen(false);
      fetchAccounts(); // Refresh to get updated data from backend
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to update operating hours' });
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
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            onClick={() => setImportDialogOpen(true)}
          >
            Import Sessions
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Add Account
          </Button>
        </Box>
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
                  <TableCell>Proxy</TableCell>
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
                      {account.proxy ? (
                        <Box>
                          <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {account.proxy.proxy_url}
                          </Typography>
                          {account.proxy.ip_address && (
                            <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                              IP: {account.proxy.ip_address}
                            </Typography>
                          )}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">None</Typography>
                      )}
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
                            disabled={account.status !== 'active' || loadingActions[account.id] === 'test'}
                          >
                            {loadingActions[account.id] === 'test' ? <CircularProgress size={16} /> : <TestIcon />}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={account.status === 'active' ? 'Pause' : 'Resume'}>
                          <IconButton
                            size="small"
                            onClick={() => handlePauseResume(account)}
                            disabled={account.status === 'pending_verification' || loadingActions[account.id] === 'pause' || loadingActions[account.id] === 'resume'}
                          >
                            {(loadingActions[account.id] === 'pause' || loadingActions[account.id] === 'resume') ?
                              <CircularProgress size={16} /> :
                              (account.status === 'active' ? <PauseIcon /> : <PlayIcon />)
                            }
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit Proxy">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenEditProxy(account)}
                            disabled={!!loadingActions[account.id]}
                          >
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Campaign Settings">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenCampaignSettings(account)}
                            disabled={!!loadingActions[account.id]}
                          >
                            <CampaignIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete Account">
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteAccount(account)}
                            color="error"
                            disabled={!!loadingActions[account.id]}
                          >
                            <DeleteIcon />
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
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <TextField
                    fullWidth
                    label="API ID"
                    type="number"
                    value={createForm.api_id || ''}
                    onChange={(e) => setCreateForm({ ...createForm, api_id: e.target.value })}
                  />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <TextField
                    fullWidth
                    label="API Hash"
                    value={createForm.api_hash}
                    onChange={(e) => setCreateForm({ ...createForm, api_hash: e.target.value })}
                  />
                </Box>
              </Box>
              <Box>
                <TextField
                  fullWidth
                  label="Phone Number"
                  placeholder="+1234567890"
                  value={createForm.phone_number}
                  onChange={(e) => setCreateForm({ ...createForm, phone_number: e.target.value })}
                />
              </Box>
              <Box>
                <TextField
                  fullWidth
                  label="Nickname"
                  value={createForm.nickname}
                  onChange={(e) => setCreateForm({ ...createForm, nickname: e.target.value })}
                />
              </Box>
              <FormControl fullWidth>
                <InputLabel id="proxy-select-label">Proxy (Optional)</InputLabel>
                <Select
                  labelId="proxy-select-label"
                  value={createForm.proxy_id}
                  label="Proxy (Optional)"
                  onChange={(e) => setCreateForm({ ...createForm, proxy_id: e.target.value as number | '' })}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  {proxies.map((proxy) => (
                    <MenuItem key={proxy.id} value={proxy.id}>
                      {proxy.proxy_url}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
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

      {/* Edit Proxy Dialog */}
      <Dialog open={editProxyDialogOpen} onClose={() => setEditProxyDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Proxy for {selectedAccount?.nickname}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="edit-proxy-select-label">Proxy</InputLabel>
              <Select
                labelId="edit-proxy-select-label"
                value={selectedProxyId}
                label="Proxy"
                onChange={(e) => setSelectedProxyId(e.target.value as number | '')}
              >
                <MenuItem value="">
                  <em>None (Remove Proxy)</em>
                </MenuItem>
                {proxies.map((proxy) => (
                  <MenuItem key={proxy.id} value={proxy.id}>
                    {proxy.proxy_url}
                    {proxy.ip_address && ` (IP: ${proxy.ip_address})`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditProxyDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateProxy} variant="contained">Update Proxy</Button>
        </DialogActions>
      </Dialog>

      {/* Campaign Settings Dialog */}
      <Dialog open={campaignSettingsDialogOpen} onClose={() => setCampaignSettingsDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Account Operating Hours: {selectedAccount?.nickname}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Typography variant="subtitle2">Sleep Hours (Pause Activity During These Hours)</Typography>
            <Box display="flex" gap={2}>
              <TextField
                label="Sleep Start (Hour)"
                type="number"
                size="small"
                value={operatingHours.sleep_hour_start}
                onChange={(e) => setOperatingHours({ ...operatingHours, sleep_hour_start: parseInt(e.target.value) })}
                inputProps={{ min: 0, max: 23 }}
                helperText="Hour to start sleeping (0-23)"
              />
              <TextField
                label="Sleep End (Hour)"
                type="number"
                size="small"
                value={operatingHours.sleep_hour_end}
                onChange={(e) => setOperatingHours({ ...operatingHours, sleep_hour_end: parseInt(e.target.value) })}
                inputProps={{ min: 0, max: 23 }}
                helperText="Hour to wake up (0-23)"
              />
            </Box>

            <TextField
              label="Daily Message Limit"
              type="number"
              size="small"
              value={operatingHours.daily_message_limit}
              onChange={(e) => setOperatingHours({ ...operatingHours, daily_message_limit: parseInt(e.target.value) })}
              helperText="Maximum messages per 24h (applies to all activities)"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCampaignSettingsDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateCampaignSettings} variant="contained">Save Settings</Button>
        </DialogActions>
      </Dialog>

      {/* Import Sessions Dialog */}
      <ImportSessionsDialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        onSuccess={() => {
          setImportDialogOpen(false);
          fetchAccounts();
        }}
      />
    </Box>
  );
}
