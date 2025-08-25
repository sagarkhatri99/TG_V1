import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import api, { endpoints } from '../api';

const steps = ['Enter Details', 'Verify OTP', 'Download CSV'];

export default function ScrapeUsers() {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  const [formData, setFormData] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    code: '',
    group_username: '',
  });

  const handleSendOTP = async () => {
    setLoading(true);
    try {
      await api.post(endpoints.scraping.startAuth, {
        api_id: parseInt(formData.api_id),
        api_hash: formData.api_hash,
        phone_number: formData.phone_number,
      });
      setAlert({ type: 'success', message: 'OTP sent to your phone!' });
      setActiveStep(1);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to send OTP' });
    } finally {
      setLoading(false);
    }
  };

  const handleScrape = async () => {
    setLoading(true);
    try {
      const response = await api.post(endpoints.scraping.verifyScrape, {
        api_id: parseInt(formData.api_id),
        api_hash: formData.api_hash,
        phone_number: formData.phone_number,
        code: formData.code,
        group_username: formData.group_username,
      });
      setAlert({ type: 'success', message: response.data.message });
      setActiveStep(2);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Scraping failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const cleanPhone = formData.phone_number.replace('+', '');
    const downloadUrl = `${endpoints.scraping.download}?phone_number=${cleanPhone}`;
    window.open(`http://localhost:8000${downloadUrl}`, '_blank');
  };

  const handleReset = () => {
    setActiveStep(0);
    setFormData({
      api_id: '',
      api_hash: '',
      phone_number: '',
      code: '',
      group_username: '',
    });
    setAlert(null);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Scrape Users from Telegram Groups
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Extract user information from Telegram groups and export to CSV.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

          {activeStep === 0 && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API ID"
                  type="number"
                  value={formData.api_id}
                  onChange={(e) => setFormData({ ...formData, api_id: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API Hash"
                  value={formData.api_hash}
                  onChange={(e) => setFormData({ ...formData, api_hash: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  placeholder="+1234567890"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Group Username"
                  placeholder="@groupname or https://t.me/groupname"
                  value={formData.group_username}
                  onChange={(e) => setFormData({ ...formData, group_username: e.target.value })}
                  sx={{ mb: 3 }}
                />
              </Grid>
              <Grid item xs={12}>
                <Button
                  variant="contained"
                  onClick={handleSendOTP}
                  disabled={loading || !formData.api_id || !formData.api_hash || !formData.phone_number || !formData.group_username}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Send OTP & Start Scraping'}
                </Button>
              </Grid>
            </Grid>
          )}

          {activeStep === 1 && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="body1" gutterBottom>
                  Enter the OTP code sent to {formData.phone_number}
                </Typography>
                <TextField
                  fullWidth
                  label="OTP Code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  sx={{ mb: 3 }}
                />
                <Button
                  variant="contained"
                  onClick={handleScrape}
                  disabled={loading || !formData.code}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Verify & Scrape Users'}
                </Button>
              </Grid>
            </Grid>
          )}

          {activeStep === 2 && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Scraping Complete! 🎉
                </Typography>
                <Typography variant="body1" gutterBottom>
                  Your CSV file is ready for download.
                </Typography>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={handleDownload}
                  >
                    Download CSV
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleReset}
                  >
                    Scrape Another Group
                  </Button>
                </Box>
              </Grid>
            </Grid>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
