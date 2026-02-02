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
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import api from '../api/Index';


interface Account {
  id: number;
  nickname: string;
  phone_number: string;
  status: string;
}

export default function ScrapeUsers() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<number | ''>('');
  const [groupUsername, setGroupUsername] = useState('');
  const [loadingAccounts, setLoadingAccounts] = useState(true);


  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/api/accounts/list');
      const activeAccounts = (response.data || []).filter(
        (acc: any) => acc.status === 'active'
      );
      setAccounts(activeAccounts);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to load accounts' });
    } finally {
      setLoadingAccounts(false);
    }
  };

  const handleScrape = async () => {
    if (!selectedAccount || !groupUsername) {
      setAlert({ type: 'error', message: 'Please select an account and enter group username' });
      return;
    }

    setLoading(true);
    setAlert(null);
    try {
      const response = await api.post('/api/scrape-users/scrape-with-account', {
        account_id: selectedAccount,
        group_username: groupUsername,
      });
      setAlert({
        type: 'success',
        message: `${response.data.message}. Check the Jobs page to monitor progress and download results.`
      });
      // Reset form after successful job creation
      setTimeout(() => {
        setSelectedAccount('');
        setGroupUsername('');
      }, 3000);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Scraping failed' });
    } finally {
      setLoading(false);
    }
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
          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

          {loadingAccounts ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <FormControl fullWidth>
                <InputLabel>Select Telegram Account</InputLabel>
                <Select
                  value={selectedAccount}
                  label="Select Telegram Account"
                  onChange={(e) => setSelectedAccount(e.target.value as number)}
                >
                  {accounts.map((account) => (
                    <MenuItem key={account.id} value={account.id}>
                      {account.nickname} ({account.phone_number})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                fullWidth
                label="Group Username"
                placeholder="@groupname or https://t.me/groupname"
                value={groupUsername}
                onChange={(e) => setGroupUsername(e.target.value)}
                helperText="Enter the Telegram group username or link"
              />

              <Button
                variant="contained"
                onClick={handleScrape}
                disabled={loading || !selectedAccount || !groupUsername}
                fullWidth
                size="large"
              >
                {loading ? <CircularProgress size={24} /> : 'Start Scraping Job'}
              </Button>

              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                💡 The scraping will run as a background job. Check the "Jobs" page to monitor progress and download results when complete.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
