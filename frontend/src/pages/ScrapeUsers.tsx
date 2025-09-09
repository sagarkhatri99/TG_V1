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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import api, { endpoints } from '../api/Index';
import type { TelegramAccount } from '../Types/Index';

export default function ScrapeUsers() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  
  const [formData, setFormData] = useState({
    account_id: '',
    group_username: '',
  });

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await api.get(endpoints.accounts.list);
        // Filter for active accounts as only they can be used for jobs
        const activeAccounts = response.data.accounts.filter((acc: TelegramAccount) => acc.status === 'active');
        setAccounts(activeAccounts);
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
      const response = await api.post('/api/scrape-users/create-job', {
        account_id: parseInt(formData.account_id),
        group_username: formData.group_username,
      });
      setAlert({ type: 'success', message: `Scrape job created successfully (Job ID: ${response.data.job_id}). You can monitor its progress on the Jobs page.` });
      // Reset form
      setFormData({ account_id: '', group_username: '' });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create job' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Scrape Users from Group
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Create a job to scrape all members from a public Telegram group. The results will be available for download on the Jobs page.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: '600px' }}>
            <FormControl fullWidth>
              <InputLabel id="account-select-label">Select Account to Use</InputLabel>
              <Select
                labelId="account-select-label"
                value={formData.account_id}
                label="Select Account to Use"
                onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
              >
                {accounts.length > 0 ? (
                  accounts.map((account) => (
                    <MenuItem key={account.id} value={account.id}>
                      {account.nickname} ({account.phone_number})
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled>No active accounts found. Please add and verify an account first.</MenuItem>
                )}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Target Group Username"
              placeholder="@groupname or https://t.me/groupname"
              value={formData.group_username}
              onChange={(e) => setFormData({ ...formData, group_username: e.target.value })}
            />

            <Button
              variant="contained"
              startIcon={<SendIcon />}
              onClick={handleCreateJob}
              disabled={loading || !formData.account_id || !formData.group_username}
              fullWidth
            >
              {loading ? <CircularProgress size={24} /> : 'Create Scrape Job'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
