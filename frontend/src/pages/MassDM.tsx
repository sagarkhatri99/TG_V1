import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,  // Add this
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';

import { Send as SendIcon, Upload as UploadIcon } from '@mui/icons-material';
import api, { endpoints } from '../api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function MassDM() {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  // Bot DM state
  const [botForm, setBotForm] = useState({
    bot_token: '',
    message: '',
    file: null as File | null,
  });

  // Account DM state
  const [accountForm, setAccountForm] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    otp: '',
    message: '',
    file: null as File | null,
  });
  const [otpSent, setOtpSent] = useState(false);

  const handleBotDM = async () => {
    if (!botForm.file) {
      setAlert({ type: 'error', message: 'Please upload a CSV file with chat IDs' });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('bot_token', botForm.bot_token);
      formData.append('message', botForm.message);
      formData.append('file', botForm.file);

      const response = await api.post(endpoints.massDM.bot, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setAlert({ type: 'success', message: response.data.message });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to send messages' });
    } finally {
      setLoading(false);
    }
  };

  const handleSendOTP = async () => {
    setLoading(true);
    try {
      await api.post(endpoints.massDM.account.startAuth, {
        api_id: parseInt(accountForm.api_id),
        api_hash: accountForm.api_hash,
        phone_number: accountForm.phone_number,
      });
      setAlert({ type: 'success', message: 'OTP sent to your phone!' });
      setOtpSent(true);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to send OTP' });
    } finally {
      setLoading(false);
    }
  };

  const handleAccountDM = async () => {
    if (!accountForm.file) {
      setAlert({ type: 'error', message: 'Please upload a CSV file with user IDs or usernames' });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('api_id', accountForm.api_id);
      formData.append('api_hash', accountForm.api_hash);
      formData.append('phone_number', accountForm.phone_number);
      formData.append('otp', accountForm.otp);
      formData.append('message', accountForm.message);
      formData.append('file', accountForm.file);

      const response = await api.post(endpoints.massDM.account.send, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setAlert({ type: 'success', message: response.data.message });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to send messages' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Mass Direct Messages
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Send bulk direct messages using either a Telegram bot or your personal account.
      </Typography>

      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
          {alert.message}
        </Alert>
      )}

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="Via Bot" />
            <Tab label="Via Account" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Use a Telegram bot to send messages. Requires bot token and CSV with chat_id column.
            </Typography>
            <Divider sx={{ my: 2 }} />

            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Bot Token"
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                  value={botForm.bot_token}
                  onChange={(e) => setBotForm({ ...botForm, bot_token: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Message"
                  placeholder="Your message here..."
                  value={botForm.message}
                  onChange={(e) => setBotForm({ ...botForm, message: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="outlined"
                  component="label"
                  startIcon={<UploadIcon />}
                  sx={{ mb: 2 }}
                >
                  Upload CSV File (chat_id column required)
                  <input
                    type="file"
                    accept=".csv"
                    hidden
                    onChange={(e) => setBotForm({ ...botForm, file: e.target.files?.[0] || null })}
                  />
                </Button>
                {botForm.file && (
                  <Typography variant="body2" color="text.secondary">
                    Selected: {botForm.file.name}
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  startIcon={<SendIcon />}
                  onClick={handleBotDM}
                  disabled={loading || !botForm.bot_token || !botForm.message || !botForm.file}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Send Messages via Bot'}
                </Button>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Use your personal Telegram account to send messages. More features but requires verification.
            </Typography>
            <Divider sx={{ my: 2 }} />

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API ID"
                  type="number"
                  value={accountForm.api_id}
                  onChange={(e) => setAccountForm({ ...accountForm, api_id: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API Hash"
                  value={accountForm.api_hash}
                  onChange={(e) => setAccountForm({ ...accountForm, api_hash: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  placeholder="+1234567890"
                  value={accountForm.phone_number}
                  onChange={(e) => setAccountForm({ ...accountForm, phone_number: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>

              {!otpSent ? (
                <Grid item xs={12}>
                  <Button
                    variant="outlined"
                    onClick={handleSendOTP}
                    disabled={loading || !accountForm.api_id || !accountForm.api_hash || !accountForm.phone_number}
                    fullWidth
                  >
                    {loading ? <CircularProgress size={24} /> : 'Send OTP'}
                  </Button>
                </Grid>
              ) : (
                <>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="OTP Code"
                      value={accountForm.otp}
                      onChange={(e) => setAccountForm({ ...accountForm, otp: e.target.value })}
                      sx={{ mb: 2 }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      label="Message"
                      placeholder="Your message here..."
                      value={accountForm.message}
                      onChange={(e) => setAccountForm({ ...accountForm, message: e.target.value })}
                      sx={{ mb: 2 }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="outlined"
                      component="label"
                      startIcon={<UploadIcon />}
                      sx={{ mb: 2 }}
                    >
                      Upload CSV File (user_id or username column)
                      <input
                        type="file"
                        accept=".csv"
                        hidden
                        onChange={(e) => setAccountForm({ ...accountForm, file: e.target.files?.[0] || null })}
                      />
                    </Button>
                    {accountForm.file && (
                      <Typography variant="body2" color="text.secondary">
                        Selected: {accountForm.file.name}
                      </Typography>
                    )}
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      startIcon={<SendIcon />}
                      onClick={handleAccountDM}
                      disabled={loading || !accountForm.otp || !accountForm.message || !accountForm.file}
                      fullWidth
                    >
                      {loading ? <CircularProgress size={24} /> : 'Send Messages via Account'}
                    </Button>
                  </Grid>
                </>
              )}
            </Grid>
          </TabPanel>
        </CardContent>
      </Card>
    </Box>
  );
}
