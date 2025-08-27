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
import { Campaign as CampaignIcon } from '@mui/icons-material';
import api, { endpoints } from '/src/api/Index';
import { TelegramAccount } from '/src/Types/Index';

export default function AutoPromo() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  
  const [formData, setFormData] = useState({
    account_id: '',
    target_group: '',
    promo_message: '',
    interval_seconds: '3600',
    use_random_interval: false,
    min_interval: '60',
    max_interval: '300',
    stop_after_hours: '',
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

  const handleCreateJob = async () => {
    setLoading(true);
    setAlert(null);
    try {
      const payload = {
        account_id: parseInt(formData.account_id),
        target_group: formData.target_group,
        promo_message: formData.promo_message,
        interval_seconds: parseInt(formData.interval_seconds),
        use_random_interval: formData.use_random_interval,
        min_interval: formData.use_random_interval ? parseInt(formData.min_interval) : null,
        max_interval: formData.use_random_interval ? parseInt(formData.max_interval) : null,
        stop_after_hours: formData.stop_after_hours ? parseInt(formData.stop_after_hours) : null,
      };
      const response = await api.post('/api/auto_promo/create-job', payload);
      setAlert({ type: 'success', message: response.data.message || 'Job created successfully!' });
      // Optionally reset form
      setFormData({ ...formData, target_group: '', promo_message: '' });
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
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.use_random_interval}
                    onChange={(e) => setFormData({ ...formData, use_random_interval: e.target.checked })}
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
                  onChange={(e) => setFormData({ ...formData, min_interval: e.target.value })}
                />
                <TextField
                  fullWidth
                  label="Max Interval (s)"
                  type="number"
                  value={formData.max_interval}
                  onChange={(e) => setFormData({ ...formData, max_interval: e.target.value })}
                />
              </Box>
            ) : (
              <TextField
                fullWidth
                label="Interval"
                type="number"
                value={formData.interval_seconds}
                onChange={(e) => setFormData({ ...formData, interval_seconds: e.target.value })}
                InputProps={{
                  endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                }}
              />
            )}

            <Box>
              <TextField
                fullWidth
                label="Stop After (hours)"
                type="number"
                placeholder="Optional"
                value={formData.stop_after_hours}
                onChange={(e) => setFormData({ ...formData, stop_after_hours: e.target.value })}
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
