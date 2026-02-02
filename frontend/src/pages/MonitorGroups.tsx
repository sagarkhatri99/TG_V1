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
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Add as AddIcon, Send as SendIcon } from '@mui/icons-material';
import api, { endpoints } from '../api/Index';
import type { TelegramAccount } from '../Types/Index'; // Assuming you have this type defined

export default function MonitorGroups() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  
  const [formData, setFormData] = useState({
    account_id: '',
    group_usernames: [] as string[],
    keywords: [] as string[],
    monitored_users: [] as string[],
    limit: '100',
    days: '7', // default to 7 days
  });

  const [currentGroup, setCurrentGroup] = useState('');
  const [currentKeyword, setCurrentKeyword] = useState('');
  const [currentUser, setCurrentUser] = useState('');

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await api.get(endpoints.accounts.list);
        setAccounts(response.data || []);
      } catch (error) {
        setAlert({ type: 'error', message: 'Failed to fetch accounts.' });
      }
    };
    fetchAccounts();
  }, []);

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

  const handleCreateJob = async () => {
    setLoading(true);
    setAlert(null);
    try {
      const response = await api.post('/api/group-monitor/create-job', {
        account_id: parseInt(formData.account_id),
        group_usernames: formData.group_usernames,
        keywords: formData.keywords,
        monitored_users: formData.monitored_users,
        limit: parseInt(formData.limit),
        days: parseInt(formData.days),
      });
      setAlert({ type: 'success', message: response.data.message || 'Job created successfully!' });
      // Optionally reset form
      setFormData({ ...formData, group_usernames: [], keywords: [], monitored_users: [] });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create job' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Monitor Telegram Groups
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Create a job to monitor groups for specific keywords and users.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

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

              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Button
                  variant={formData.days === '1' ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, days: '1' })}
                >
                  Past 1 day
                </Button>
                <Button
                  variant={formData.days === '7' ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, days: '7' })}
                >
                  Past 7 days
                </Button>
              </Box>

              <Button
                variant="contained"
                startIcon={<SendIcon />}
                onClick={handleCreateJob}
                disabled={loading || !formData.account_id || formData.group_usernames.length === 0}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : 'Create Monitoring Job'}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
