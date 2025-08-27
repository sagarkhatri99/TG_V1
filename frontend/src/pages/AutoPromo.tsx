import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Alert,
  CircularProgress,
  InputAdornment,
} from '@mui/material';
import { Campaign as CampaignIcon } from '@mui/icons-material';
import api, { endpoints } from '../api';


export default function AutoPromo() {
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  const [formData, setFormData] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    otp: '',
    target_group: '',
    promo_message: '',
    interval_seconds: '3600',
  });


  const handleSendOTP = async () => {
    setLoading(true);
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('api_id', formData.api_id);
      formDataToSend.append('api_hash', formData.api_hash);
      formDataToSend.append('phone_number', formData.phone_number);


      await api.post(endpoints.autoPromo.startAuth, formDataToSend, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });


      setAlert({ type: 'success', message: 'OTP sent to your phone!' });
      setOtpSent(true);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to send OTP' });
    } finally {
      setLoading(false);
    }
  };


  const handleStartPromo = async () => {
    setLoading(true);
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('api_id', formData.api_id);
      formDataToSend.append('api_hash', formData.api_hash);
      formDataToSend.append('phone_number', formData.phone_number);
      formDataToSend.append('otp', formData.otp);
      formDataToSend.append('target_group', formData.target_group);
      formDataToSend.append('promo_message', formData.promo_message);
      formDataToSend.append('interval_seconds', formData.interval_seconds);


      const response = await api.post(endpoints.autoPromo.start, formDataToSend, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });


      setAlert({ type: 'success', message: response.data || 'Auto promo started successfully!' });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to start auto promo' });
    } finally {
      setLoading(false);
    }
  };


  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Auto Promo Campaign
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Automatically send promotional messages to target groups at specified intervals.
      </Typography>


      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
          {alert.message}
        </Alert>
      )}


      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
              <Box sx={{ flex: 1 }}>
                <TextField
                  fullWidth
                  label="API ID"
                  type="number"
                  value={formData.api_id}
                  onChange={(e) => setFormData({ ...formData, api_id: e.target.value })}
                  disabled={otpSent}
                  sx={{ mb: 2 }}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <TextField
                  fullWidth
                  label="API Hash"
                  value={formData.api_hash}
                  onChange={(e) => setFormData({ ...formData, api_hash: e.target.value })}
                  disabled={otpSent}
                  sx={{ mb: 2 }}
                />
              </Box>
            </Box>
            <Box>
              <TextField
                fullWidth
                label="Phone Number"
                placeholder="+1234567890"
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                disabled={otpSent}
                sx={{ mb: 2 }}
              />
            </Box>


            {!otpSent ? (
              <Box>
                <Button
                  variant="contained"
                  onClick={handleSendOTP}
                  disabled={loading || !formData.api_id || !formData.api_hash || !formData.phone_number}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Send OTP'}
                </Button>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Box>
                  <TextField
                    fullWidth
                    label="OTP Code"
                    value={formData.otp}
                    onChange={(e) => setFormData({ ...formData, otp: e.target.value })}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box>
                  <TextField
                    fullWidth
                    label="Target Group"
                    placeholder="@groupname or https://t.me/groupname"
                    value={formData.target_group}
                    onChange={(e) => setFormData({ ...formData, target_group: e.target.value })}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box>
                  <TextField
                    fullWidth
                    multiline
                    rows={4}
                    label="Promotional Message"
                    placeholder="Your promotional message here..."
                    value={formData.promo_message}
                    onChange={(e) => setFormData({ ...formData, promo_message: e.target.value })}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box>
                  <TextField
                    fullWidth
                    label="Interval"
                    type="number"
                    value={formData.interval_seconds}
                    onChange={(e) => setFormData({ ...formData, interval_seconds: e.target.value })}
                    InputProps={{
                      endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                    }}
                    sx={{ mb: 3 }}
                  />
                </Box>
                <Box>
                  <Button
                    variant="contained"
                    startIcon={<CampaignIcon />}
                    onClick={handleStartPromo}
                    disabled={loading || !formData.otp || !formData.target_group || !formData.promo_message}
                    fullWidth
                  >
                    {loading ? <CircularProgress size={24} /> : 'Start Auto Promo'}
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
