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
  RadioGroup,
  FormControlLabel,
  Radio,
} from '@mui/material';
import { Send as SendIcon, Upload as UploadIcon } from '@mui/icons-material';
import api from '../api/Index';
import type { TelegramAccount } from '../Types/Index';

type DmMethod = 'account' | 'bot';

export default function MassDM() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [dmMethod, setDmMethod] = useState<DmMethod>('account');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  
  const [formData, setFormData] = useState({
    account_id: '',
    bot_token: '',
    message: '',
    stop_after_hours: '',
  });

  useEffect(() => {
    if (dmMethod === 'account') {
      const fetchAccounts = async () => {
        try {
          const response = await api.get('/api/accounts/list');
          setAccounts(response.data.accounts);
        } catch (error) {
          setAlert({ type: 'error', message: 'Failed to fetch accounts.' });
        }
      };
      fetchAccounts();
    }
  }, [dmMethod]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setCsvFile(event.target.files[0]);
    }
  };

  const handleCreateJob = async () => {
    if (!csvFile) {
      setAlert({ type: 'error', message: 'Please upload a CSV file.' });
      return;
    }

    setLoading(true);
    setAlert(null);

    const apiFormData = new FormData();
    apiFormData.append('message', formData.message);
    apiFormData.append('csv_file', csvFile);
    if (formData.stop_after_hours) {
      apiFormData.append('stop_after_hours', formData.stop_after_hours);
    }

    let url = '';
    if (dmMethod === 'account') {
      url = '/api/mass-dm-account/create-job';
      apiFormData.append('account_id', formData.account_id);
    } else {
      url = '/api/mass-dm-bot/create-job';
      apiFormData.append('bot_token', formData.bot_token);
    }

    try {
      const response = await api.post(url, apiFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAlert({ type: 'success', message: response.data.message || 'Job created successfully!' });
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create job' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Mass DM
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Create a job to send a direct message to a list of users.
      </Typography>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <FormControl component="fieldset">
              <RadioGroup row value={dmMethod} onChange={(e) => setDmMethod(e.target.value as DmMethod)}>
                <FormControlLabel value="account" control={<Radio />} label="Using Account" />
                <FormControlLabel value="bot" control={<Radio />} label="Using Bot Token" />
              </RadioGroup>
            </FormControl>

            {dmMethod === 'account' ? (
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
            ) : (
              <TextField
                fullWidth
                label="Bot Token"
                value={formData.bot_token}
                onChange={(e) => setFormData({ ...formData, bot_token: e.target.value })}
              />
            )}

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Message"
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
            />

            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
            >
              Upload CSV
              <input type="file" hidden accept=".csv" onChange={handleFileChange} />
            </Button>
            {csvFile && <Typography variant="body2">{csvFile.name}</Typography>}

            <TextField
              fullWidth
              label="Stop After (hours)"
              type="number"
              placeholder="Optional"
              value={formData.stop_after_hours}
              onChange={(e) => setFormData({ ...formData, stop_after_hours: e.target.value })}
            />

            <Button
              variant="contained"
              startIcon={<SendIcon />}
              onClick={handleCreateJob}
              disabled={loading || (dmMethod === 'account' && !formData.account_id) || (dmMethod === 'bot' && !formData.bot_token) || !formData.message || !csvFile}
              fullWidth
            >
              {loading ? <CircularProgress size={24} /> : 'Create Mass DM Job'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
