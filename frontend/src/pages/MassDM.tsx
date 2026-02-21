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
import { Send as SendIcon, Upload as UploadIcon, Info as InfoIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import api from '../api/Index';
import type { TelegramAccount, Template } from '../Types/Index';

type DmMethod = 'account' | 'bot';

export default function MassDM() {
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | ''>('');
  const [previewMessages, setPreviewMessages] = useState<string[]>([]);
  const [dmMethod, setDmMethod] = useState<DmMethod>('account');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);

  const [formData, setFormData] = useState({
    account_id: '',
    bot_token: '',
    message: '',
    user_description: '',
    stop_after_hours: '',
    rate_limit_per_hour: '20',
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  useEffect(() => {
    if (dmMethod === 'account') {
      const fetchAccounts = async () => {
        try {
          const response = await api.get('/api/accounts/list');
          const activeAccounts = (response.data || []).filter(
            (acc: TelegramAccount) => acc.status === 'active'
          );
          setAccounts(activeAccounts);
        } catch (error) {
          setAlert({ type: 'error', message: 'Failed to fetch accounts.' });
        }
      };
      fetchAccounts();
    }
  }, [dmMethod]);

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/api/templates');
      setTemplates(response.data || []);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };

  const handleTemplateSelect = async (templateId: number | '') => {
    setSelectedTemplateId(templateId);

    if (templateId === '') {
      setPreviewMessages([]);
      return;
    }

    try {
      const response = await api.get(`/api/templates/${templateId}/preview?count=3`);
      setPreviewMessages(response.data.samples || []);
    } catch (error) {
      console.error('Failed to fetch preview:', error);
      setAlert({ type: 'error', message: 'Failed to generate preview messages' });
    }
  };

  const refreshPreview = async () => {
    if (selectedTemplateId) {
      handleTemplateSelect(selectedTemplateId);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, fileType: 'csv' | 'image') => {
    if (event.target.files) {
      if (fileType === 'csv') {
        setCsvFile(event.target.files[0]);
      } else {
        setImageFile(event.target.files[0]);
      }
    }
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

    setLoading(true);
    setAlert(null);

    const apiFormData = new FormData();

    // Add template_id or manual message
    if (selectedTemplateId) {
      apiFormData.append('template_id', selectedTemplateId.toString());
    } else if (formData.message) {
      apiFormData.append('message', formData.message);
    }

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

            <FormControl fullWidth>
              <InputLabel id="template-select-label">Message Template (Optional)</InputLabel>
              <Select
                labelId="template-select-label"
                value={selectedTemplateId}
                label="Message Template (Optional)"
                onChange={(e) => handleTemplateSelect(e.target.value as number | '')}
              >
                <MenuItem value="">Manual Message (No Template)</MenuItem>
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name} ({template.category})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {selectedTemplateId && previewMessages.length > 0 && (
              <Alert severity="info" sx={{ mt: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2">Sample Generated Messages:</Typography>
                  <Button size="small" startIcon={<RefreshIcon />} onClick={refreshPreview}>
                    Regenerate
                  </Button>
                </Box>
                {previewMessages.map((msg, idx) => (
                  <Box key={idx} sx={{ mb: 1, p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
                    <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                      "{msg}"
                    </Typography>
                  </Box>
                ))}
              </Alert>
            )}

            {!selectedTemplateId && (
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Message"
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              />
            )}

            <TextField
              fullWidth
              label="Job Description (Optional)"
              placeholder="Describe what this mass DM campaign is for..."
              value={formData.user_description}
              onChange={(e) => setFormData({ ...formData, user_description: e.target.value })}
            />

            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                component="label"
                startIcon={<UploadIcon />}
              >
                Upload CSV File
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

            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
            >
              Upload Image (Optional)
              <input type="file" hidden accept="image/*" onChange={(e) => handleFileChange(e, 'image')} />
            </Button>
            {imageFile && <Typography variant="body2">Image: {imageFile.name}</Typography>}

            <TextField
              fullWidth
              label="Stop After (hours)"
              type="number"
              placeholder="Optional"
              value={formData.stop_after_hours}
              onChange={(e) => setFormData({ ...formData, stop_after_hours: e.target.value })}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Rate Limit (msg/hr)"
                type="number"
                placeholder="e.g., 20"
                value={formData.rate_limit_per_hour}
                onChange={(e) => setFormData({ ...formData, rate_limit_per_hour: e.target.value })}
              />
            </Box>

            <Alert severity="info" icon={<InfoIcon />}>
              <Typography variant="body2">
                <strong>Message Pacing:</strong> Delays and timing are automatically controlled by backend safety logic and account-level settings (sleep hours, daily limits). No manual delay configuration needed.
              </Typography>
            </Alert>

            <Button
              variant="contained"
              startIcon={<SendIcon />}
              onClick={handleCreateJob}
              disabled={loading || (dmMethod === 'account' && !formData.account_id) || (dmMethod === 'bot' && !formData.bot_token) || (!formData.message && !selectedTemplateId) || !csvFile}
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
