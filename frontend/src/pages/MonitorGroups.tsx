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
  Stepper,
  Step,
  StepLabel,
  Chip,
} from '@mui/material';

import { Download as DownloadIcon, Add as AddIcon } from '@mui/icons-material';
import api, { endpoints } from '../api';


const steps = ['Enter Details', 'Verify OTP', 'Download Results'];


export default function MonitorGroups() {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  
  const [formData, setFormData] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    code: '',
    group_usernames: [] as string[],
    keywords: [] as string[],
    monitored_users: [] as string[],
    limit: '50',
  });


  const [currentGroup, setCurrentGroup] = useState('');
  const [currentKeyword, setCurrentKeyword] = useState('');
  const [currentUser, setCurrentUser] = useState('');


  const addGroup = () => {
    if (currentGroup && !formData.group_usernames.includes(currentGroup)) {
      setFormData({ ...formData, group_usernames: [...formData.group_usernames, currentGroup] });
      setCurrentGroup('');
    }
  };


  const addKeyword = () => {
    if (currentKeyword && !formData.keywords.includes(currentKeyword)) {
      setFormData({ ...formData, keywords: [...formData.keywords, currentKeyword] });
      setCurrentKeyword('');
    }
  };


  const addUser = () => {
    if (currentUser && !formData.monitored_users.includes(currentUser)) {
      setFormData({ ...formData, monitored_users: [...formData.monitored_users, currentUser] });
      setCurrentUser('');
    }
  };


  const removeItem = (array: string[], item: string, field: string) => {
    setFormData({
      ...formData,
      [field]: array.filter(i => i !== item),
    });
  };


  const handleSendOTP = async () => {
    setLoading(true);
    try {
      await api.post(endpoints.monitoring.startAuth, {
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


  const handleMonitor = async () => {
    setLoading(true);
    try {
      const response = await api.post(endpoints.monitoring.verifyMonitor, {
        api_id: parseInt(formData.api_id),
        api_hash: formData.api_hash,
        phone_number: formData.phone_number,
        code: formData.code,
        group_usernames: formData.group_usernames,
        keywords: formData.keywords,
        monitored_users: formData.monitored_users,
        limit: parseInt(formData.limit),
      });
      setAlert({ type: 'success', message: response.data.message });
      setActiveStep(2);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Monitoring failed' });
    } finally {
      setLoading(false);
    }
  };


  const handleDownload = () => {
    const cleanPhone = formData.phone_number.replace('+', '');
    const downloadUrl = `${endpoints.monitoring.download}?phone_number=${cleanPhone}`;
    window.open(`http://localhost:8000${downloadUrl}`, '_blank');
  };


  const handleReset = () => {
    setActiveStep(0);
    setFormData({
      api_id: '',
      api_hash: '',
      phone_number: '',
      code: '',
      group_usernames: [],
      keywords: [],
      monitored_users: [],
      limit: '50',
    });
    setAlert(null);
  };


  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Monitor Telegram Groups
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Monitor groups for specific keywords and users, then export matching messages.
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
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
                <Box sx={{ flex: 1 }}>
                  <TextField
                    fullWidth
                    label="API ID"
                    type="number"
                    value={formData.api_id}
                    onChange={(e) => setFormData({ ...formData, api_id: e.target.value })}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <TextField
                    fullWidth
                    label="API Hash"
                    value={formData.api_hash}
                    onChange={(e) => setFormData({ ...formData, api_hash: e.target.value })}
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
                  sx={{ mb: 2 }}
                />
              </Box>
              
              <Box>
                <Typography variant="h6" gutterBottom>Group Usernames</Typography>
                <Box display="flex" gap={1} mb={2}>
                  <TextField
                    fullWidth
                    placeholder="@groupname"
                    value={currentGroup}
                    onChange={(e) => setCurrentGroup(e.target.value)}
                  />
                  <Button variant="outlined" onClick={addGroup} startIcon={<AddIcon />}>
                    Add
                  </Button>
                </Box>
                <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
                  {formData.group_usernames.map((group) => (
                    <Chip
                      key={group}
                      label={group}
                      onDelete={() => removeItem(formData.group_usernames, group, 'group_usernames')}
                    />
                  ))}
                </Box>
              </Box>

              <Box>
                <Typography variant="h6" gutterBottom>Keywords to Monitor</Typography>
                <Box display="flex" gap={1} mb={2}>
                  <TextField
                    fullWidth
                    placeholder="keyword"
                    value={currentKeyword}
                    onChange={(e) => setCurrentKeyword(e.target.value)}
                  />
                  <Button variant="outlined" onClick={addKeyword} startIcon={<AddIcon />}>
                    Add
                  </Button>
                </Box>
                <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
                  {formData.keywords.map((keyword) => (
                    <Chip
                      key={keyword}
                      label={keyword}
                      color="primary"
                      onDelete={() => removeItem(formData.keywords, keyword, 'keywords')}
                    />
                  ))}
                </Box>
              </Box>

              <Box>
                <Typography variant="h6" gutterBottom>Users to Monitor (Optional)</Typography>
                <Box display="flex" gap={1} mb={2}>
                  <TextField
                    fullWidth
                    placeholder="username"
                    value={currentUser}
                    onChange={(e) => setCurrentUser(e.target.value)}
                  />
                  <Button variant="outlined" onClick={addUser} startIcon={<AddIcon />}>
                    Add
                  </Button>
                </Box>
                <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
                  {formData.monitored_users.map((user) => (
                    <Chip
                      key={user}
                      label={user}
                      color="secondary"
                      onDelete={() => removeItem(formData.monitored_users, user, 'monitored_users')}
                    />
                  ))}
                </Box>
              </Box>

              <Box>
                <TextField
                  fullWidth
                  label="Message Limit"
                  type="number"
                  value={formData.limit}
                  onChange={(e) => setFormData({ ...formData, limit: e.target.value })}
                  sx={{ mb: 3 }}
                />
                <Button
                  variant="contained"
                  onClick={handleSendOTP}
                  disabled={loading || !formData.api_id || !formData.api_hash || !formData.phone_number}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Send OTP & Start Monitoring'}
                </Button>
              </Box>
            </Box>
          )}

          {activeStep === 1 && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box>
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
                  onClick={handleMonitor}
                  disabled={loading || !formData.code}
                  fullWidth
                >
                  {loading ? <CircularProgress size={24} /> : 'Verify & Start Monitoring'}
                </Button>
              </Box>
            </Box>
          )}

          {activeStep === 2 && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  Monitoring Complete! 🎉
                </Typography>
                <Typography variant="body1" gutterBottom>
                  Your monitoring results CSV is ready for download.
                </Typography>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={handleDownload}
                  >
                    Download Results
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleReset}
                  >
                    Monitor Again
                  </Button>
                </Box>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
