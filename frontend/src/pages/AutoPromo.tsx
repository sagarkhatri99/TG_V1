import { FormControlLabel, Switch } from "@mui/material";
import { useState, useEffect } from 'react';
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Campaign as CampaignIcon, Upload as UploadIcon } from '@mui/icons-material';
import api, { endpoints } from '../api/Index';
import type { TelegramAccount } from '../Types/Index';

export default function AutoPromo() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [imageFile, setImageFile] = useState<File | null>(null);
  
  const [formData, setFormData] = useState({
    account_id: '',
    target_group: '',
    promo_message: '',
    user_description: '',
    interval_seconds: '3600',
    use_random_interval: false,
    min_interval: '60',
    max_interval: '300',
    stop_after_hours: '',
    rate_limit_per_hour: '20',
  });

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await api.get(endpoints.accounts.list);
        setAccounts(response.data.accounts);
      } catch (error) {
        setAlert({ type: 'error', message: 'Failed to fetch accounts.' });
      }
    };
    fetchAccounts();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setImageFile(event.target.files[0]);
    }
  };

  const handleCreateJob = async () => {
    setLoading(true);
    setAlert(null);

    const apiFormData = new FormData();
    apiFormData.append('account_id', formData.account_id);
    apiFormData.append('target_group', formData.target_group);
    apiFormData.append('promo_message', formData.promo_message);
    if (formData.user_description) {
      apiFormData.append('user_description', formData.user_description);
    }
    apiFormData.append('use_random_interval', String(formData.use_random_interval));
    if (formData.use_random_interval) {
        apiFormData.append('min_interval', formData.min_interval);
        apiFormData.append('max_interval', formData.max_interval);
    } else {
        apiFormData.append('interval_seconds', formData.interval_seconds);
    }
    if (formData.stop_after_hours) {
      apiFormData.append('stop_after_hours', formData.stop_after_hours);
    }
    if (formData.rate_limit_per_hour) {
      apiFormData.append('rate_limit_per_hour', formData.rate_limit_per_hour);
    }
    if (imageFile) {
      apiFormData.append('image_file', imageFile);
    }

    try {
      const response = await api.post('/api/auto_promo/create-job', apiFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAlert({ type: 'success', message: response.data.message || 'Job created successfully!' });
      // Optionally reset form
      setFormData({ ...formData, target_group: '', promo_message: '' });
      setImageFile(null);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create job' });
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
            <FormControl fullWidth>
              <InputLabel id="account-select-label">Select Account</InputLabel>
              <Select
                labelId="account-select-label"
                value={formData.account_id}
                label="Select Account"
                onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
              >
                {accounts.map((account) => (
                  <MenuItem key={account.id} value={account.id}>
                    {account.nickname} ({account.phone_number})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box>
              <TextField
                fullWidth
                label="Target Group"
                placeholder="@groupname or https://t.me/groupname"
                value={formData.target_group}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, target_group: e.target.value })}
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
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, promo_message: e.target.value })}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Campaign Description (Optional)"
                placeholder="Describe what this auto promo campaign is for..."
                value={formData.user_description}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, user_description: e.target.value })}
                sx={{ mb: 2 }}
              />
              <Button
                variant="outlined"
                component="label"
                startIcon={<UploadIcon />}
                sx={{ mb: 2 }}
              >
                Upload Image (Optional)
                <input type="file" hidden accept="image/*" onChange={handleFileChange} />
              </Button>
              {imageFile && <Typography variant="body2" sx={{ mb: 2 }}>Image: {imageFile.name}</Typography>}
            </Box>
            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.use_random_interval}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, use_random_interval: e.target.checked })}
                  />
                }
                label="Use Random Interval"
              />
            </Box>

            {formData.use_random_interval ? (
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Min Interval (s)"
                  type="number"
                  value={formData.min_interval}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, min_interval: e.target.value })}
                />
                <TextField
                  fullWidth
                  label="Max Interval (s)"
                  type="number"
                  value={formData.max_interval}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, max_interval: e.target.value })}
                />
              </Box>
            ) : (
              <TextField
                fullWidth
                label="Interval"
                type="number"
                value={formData.interval_seconds}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, interval_seconds: e.target.value })}
                InputProps={{
                  endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                }}
              />
            )}

            <TextField
                fullWidth
                label="Rate Limit (msg/hr)"
                type="number"
                placeholder="e.g., 20"
                value={formData.rate_limit_per_hour}
                onChange={(e) => setFormData({ ...formData, rate_limit_per_hour: e.target.value })}
            />

            <Box>
              <TextField
                fullWidth
                label="Stop After (hours)"
                type="number"
                placeholder="Optional"
                value={formData.stop_after_hours}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, stop_after_hours: e.target.value })}
                sx={{ mb: 3 }}
              />
            </Box>
            <Box>
              <Button
                variant="contained"
                startIcon={<CampaignIcon />}
                onClick={handleCreateJob}
                disabled={loading || !formData.account_id || !formData.target_group || !formData.promo_message}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : 'Create Auto Promo Job'}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
