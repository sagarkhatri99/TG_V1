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
  OutlinedInput,
  MenuItem,
  Chip,
  Paper,
  Divider,
} from '@mui/material';
import { Send as SendIcon, Upload as UploadIcon, Speed, Info as InfoIcon } from '@mui/icons-material';
import api from '../api/Index';
import type { TelegramAccount } from '../Types/Index';

export default function MassDMDistributed() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<{ total_lines: number; sample: string[] } | null>(null);

  const [formData, setFormData] = useState({
    message: '',
    user_description: '',
    account_ids: [] as number[],
    stop_after_hours: '',
    rate_limit_per_hour: '20',
    delay_seconds: '60',
    use_random_interval: false,
    min_delay_seconds: '30',
    max_delay_seconds: '120',
  });

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await api.get('/api/accounts/list');
        setAccounts(response.data.accounts.filter((a: TelegramAccount) => a.status === 'active'));
      } catch (error) {
        setAlert({ type: 'error', message: 'Failed to fetch accounts.' });
      }
    };
    fetchAccounts();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, fileType: 'csv' | 'image') => {
    if (event.target.files) {
      const file = event.target.files[0];
      if (fileType === 'csv') {
        setCsvFile(file);
        const reader = new FileReader();
        reader.onload = (e) => {
          const text = e.target?.result as string;
          const lines = text.split('\n').filter(line => line.trim());
          setCsvPreview({
            total_lines: Math.max(0, lines.length - 1),
            sample: lines.slice(0, 4),
          });
        };
        reader.readAsText(file);
      } else {
        setImageFile(file);
      }
    }
  };

  const handleAccountChange = (event: any) => {
    const value = event.target.value;
    setFormData({ ...formData, account_ids: typeof value === 'string' ? value.split(',').map(Number) : value });
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/api/jobs/mass-dm-template/download', {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mass_dm_template.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to download template' });
    }
  };

  const handleCreateJob = async () => {
    if (!csvFile) {
      setAlert({ type: 'error', message: 'Please upload a CSV file.' });
      return;
    }

    if (formData.account_ids.length < 2) {
      setAlert({ type: 'error', message: 'Please select at least 2 accounts for distribution.' });
      return;
    }

    if (!formData.message) {
      setAlert({ type: 'error', message: 'Please enter a message.' });
      return;
    }

    setLoading(true);
    setAlert(null);

    const apiFormData = new FormData();
    apiFormData.append('message', formData.message);
    apiFormData.append('account_ids', JSON.stringify(formData.account_ids));
    if (formData.user_description) {
      apiFormData.append('user_description', formData.user_description);
    }
    apiFormData.append('csv_file', csvFile);
    if (imageFile) {
      apiFormData.append('image_file', imageFile);
    }
    if (formData.stop_after_hours) {
      apiFormData.append('stop_after_hours', formData.stop_after_hours);
    }
    if (formData.rate_limit_per_hour) {
      apiFormData.append('rate_limit_per_hour', formData.rate_limit_per_hour);
    }
    if (formData.use_random_interval) {
      apiFormData.append('min_delay_seconds', formData.min_delay_seconds);
      apiFormData.append('max_delay_seconds', formData.max_delay_seconds);
    } else if (formData.delay_seconds) {
      apiFormData.append('delay_seconds', formData.delay_seconds);
    }

    try {
      const response = await api.post('/api/mass-dm-account/create-distributed-job', apiFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAlert({
        type: 'success',
        message: `Successfully created ${response.data.job_ids.length} jobs across ${response.data.num_accounts} accounts!`,
      });
      setTimeout(() => {
        setCsvFile(null);
        setImageFile(null);
        setCsvPreview(null);
        setFormData({
          message: '',
          user_description: '',
          account_ids: [],
          stop_after_hours: '',
          rate_limit_per_hour: '20',
          delay_seconds: '60',
          use_random_interval: false,
          min_delay_seconds: '30',
          max_delay_seconds: '120',
        });
      }, 2000);
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to create jobs' });
    } finally {
      setLoading(false);
    }
  };

  const usersPerAccount = csvPreview ? Math.ceil(csvPreview.total_lines / formData.account_ids.length) : 0;
  const lastAccountUsers = csvPreview
    ? csvPreview.total_lines - usersPerAccount * (formData.account_ids.length - 1)
    : 0;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Speed />
        <Box>
          <Typography variant="h4">Distributed Mass DM</Typography>
          <Typography variant="body2" color="text.secondary">
            Send messages in parallel across multiple accounts
          </Typography>
        </Box>
      </Box>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          {alert && (
            <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
              {alert.message}
            </Alert>
          )}

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 3 }}>
            <Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <FormControl fullWidth>
                  <InputLabel>Select Accounts</InputLabel>
                  <Select
                    multiple
                    value={formData.account_ids}
                    onChange={handleAccountChange}
                    input={<OutlinedInput label="Select Accounts" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => {
                          const account = accounts.find((a) => a.id === value);
                          return (
                            <Chip key={value} label={account?.nickname || `Account ${value}`} />
                          );
                        })}
                      </Box>
                    )}
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
                  multiline
                  rows={4}
                  label="Message"
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                />

                <TextField
                  fullWidth
                  label="Job Description (Optional)"
                  placeholder="What is this campaign for?"
                  value={formData.user_description}
                  onChange={(e) => setFormData({ ...formData, user_description: e.target.value })}
                />

                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Button variant="outlined" component="label" startIcon={<UploadIcon />}>
                    Upload User CSV
                    <input type="file" hidden accept=".csv" onChange={(e) => handleFileChange(e, 'csv')} />
                  </Button>

                  <Button
                    variant="text"
                    size="small"
                    startIcon={<InfoIcon />}
                    onClick={handleDownloadTemplate}
                  >
                    Download Template
                  </Button>
                </Box>

                {csvFile && <Typography variant="body2" color="success.main">✅ CSV: {csvFile.name}</Typography>}

                <Alert severity="info" icon={<InfoIcon />} sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    <strong>CSV Format Guidelines:</strong>
                  </Typography>
                  <Typography variant="caption" component="div">
                    • Required: <code>user_id</code> OR <code>username</code> column<br />
                    • <strong>Recommended</strong>: Use <code>user_id</code> (numeric) - more reliable than usernames<br />
                    • Optional: <code>first_name</code>, <code>notes</code> for your reference<br />
                    • If both columns present, <code>user_id</code> takes priority
                  </Typography>
                </Alert>

                <Button variant="outlined" component="label" startIcon={<UploadIcon />}>
                  Upload Image (Optional)
                  <input type="file" hidden accept="image/*" onChange={(e) => handleFileChange(e, 'image')} />
                </Button>
                {imageFile && <Typography variant="body2">✅ Image: {imageFile.name}</Typography>}

                <TextField
                  fullWidth
                  label="Stop After (hours)"
                  type="number"
                  placeholder="Optional"
                  value={formData.stop_after_hours}
                  onChange={(e) => setFormData({ ...formData, stop_after_hours: e.target.value })}
                />

                <TextField
                  fullWidth
                  label="Rate Limit (msg/hr)"
                  type="number"
                  value={formData.rate_limit_per_hour}
                  onChange={(e) => setFormData({ ...formData, rate_limit_per_hour: e.target.value })}
                />

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant={!formData.use_random_interval ? 'contained' : 'outlined'}
                    onClick={() => setFormData({ ...formData, use_random_interval: false })}
                  >
                    Fixed Delay
                  </Button>
                  <Button
                    variant={formData.use_random_interval ? 'contained' : 'outlined'}
                    onClick={() => setFormData({ ...formData, use_random_interval: true })}
                  >
                    Random Interval
                  </Button>
                </Box>

                {formData.use_random_interval ? (
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <TextField
                      fullWidth
                      label="Min Delay (s)"
                      type="number"
                      value={formData.min_delay_seconds}
                      onChange={(e) => setFormData({ ...formData, min_delay_seconds: e.target.value })}
                    />
                    <TextField
                      fullWidth
                      label="Max Delay (s)"
                      type="number"
                      value={formData.max_delay_seconds}
                      onChange={(e) => setFormData({ ...formData, max_delay_seconds: e.target.value })}
                    />
                  </Box>
                ) : (
                  <TextField
                    fullWidth
                    label="Delay (seconds)"
                    type="number"
                    value={formData.delay_seconds}
                    onChange={(e) => setFormData({ ...formData, delay_seconds: e.target.value })}
                  />
                )}

                <Button
                  variant="contained"
                  startIcon={<SendIcon />}
                  onClick={handleCreateJob}
                  disabled={
                    loading ||
                    formData.account_ids.length < 2 ||
                    !formData.message ||
                    !csvFile
                  }
                  fullWidth
                  size="large"
                >
                  {loading ? <CircularProgress size={24} /> : 'Create Distributed Mass DM'}
                </Button>
              </Box>
            </Box>

            <Box>
              <Paper sx={{ p: 2, backgroundColor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  📊 Distribution Preview
                </Typography>
                <Divider sx={{ my: 1 }} />

                {csvPreview ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Total Users:
                      </Typography>
                      <Typography variant="h5">{csvPreview.total_lines}</Typography>
                    </Box>

                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Selected Accounts:
                      </Typography>
                      <Typography variant="h5">{formData.account_ids.length}</Typography>
                    </Box>

                    {formData.account_ids.length > 0 && (
                      <>
                        <Divider />
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Users per Account:
                          </Typography>
                          <Typography variant="body1" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                            {usersPerAccount}
                          </Typography>
                        </Box>

                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Last Account Users:
                          </Typography>
                          <Typography variant="body1" sx={{ fontWeight: 'bold', color: 'success.main' }}>
                            {lastAccountUsers}
                          </Typography>
                        </Box>

                        <Divider />
                        <Alert severity="info" icon={false}>
                          <Typography variant="body2">
                            {`⚡ Speedup: ~${formData.account_ids.length}x faster with ${formData.account_ids.length} accounts!`}
                          </Typography>
                        </Alert>
                      </>
                    )}

                    <Divider sx={{ my: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      <strong>Sample CSV:</strong>
                    </Typography>
                    <Box
                      sx={{
                        p: 1,
                        backgroundColor: '#f5f5f5',
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                        maxHeight: '150px',
                        overflow: 'auto',
                      }}
                    >
                      {csvPreview.sample.map((line, idx) => (
                        <div key={idx}>{line}</div>
                      ))}
                    </Box>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                    📁 Upload a CSV to see preview
                  </Typography>
                )}
              </Paper>
            </Box>
          </Box>

          <Box sx={{ mt: 3, p: 2, backgroundColor: 'info.light', borderRadius: 1 }}>
            <Typography variant="body2">
              💡 <strong>Tip:</strong> Upload a CSV with user_id or username columns. Jobs run in parallel across accounts!
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
