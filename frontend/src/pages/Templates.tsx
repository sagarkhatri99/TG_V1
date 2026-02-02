import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
  IconButton,
  Chip,
  Grid,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Alert,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import api from '../api/Index';
import type { Template, TemplateCreate } from '../Types/Index';
import toast from 'react-hot-toast';

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<TemplateCreate>({
    name: '',
    category: 'general',
    content: '',
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/templates');
      setTemplates(response.data || []);
    } catch (error: any) {
      console.error('Failed to fetch templates:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to fetch templates';
      setError(errorMsg);
      toast.error(errorMsg);
      // Set empty array to prevent undefined errors
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.content) {
      toast.error('Name and content are required');
      return;
    }

    try {
      await api.post('/api/templates', formData);
      toast.success('Template created successfully!');
      setDialogOpen(false);
      setFormData({ name: '', category: 'general', content: '' });
      fetchTemplates();
    } catch (error: any) {
      console.error('Failed to create template:', error);
      toast.error(error.response?.data?.detail || 'Failed to create template');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      await api.delete(`/api/templates/${id}`);
      toast.success('Template deleted');
      fetchTemplates();
    } catch (error: any) {
      console.error('Failed to delete template:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete template');
    }
  };

  const getSpamRiskColor = (score: number): 'success' | 'warning' | 'error' => {
    if (score < 30) return 'success';
    if (score < 70) return 'warning';
    return 'error';
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            Loading templates...
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Message Templates</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
        >
          Create Template
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {templates.length === 0 ? (
        <Alert severity="info">
          No templates yet. Create your first template to reuse messages across campaigns!
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {templates.map((template) => (
            <Grid size={{ xs: 12, md: 6, lg: 4 }} key={template.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        {template.name}
                      </Typography>
                      <Chip
                        label={template.category}
                        size="small"
                        sx={{ mr: 1 }}
                      />
                      <Chip
                        label={`Spam Risk: ${template.spam_risk_score.toFixed(0)}%`}
                        size="small"
                        color={getSpamRiskColor(template.spam_risk_score)}
                      />
                    </Box>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(template.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
                    {template.content}
                  </Typography>

                  {template.variables && template.variables.length > 0 && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Variables:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                        {template.variables.map((variable: string, idx: number) => (
                          <Chip key={idx} label={variable} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  )}

                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
                    Created: {new Date(template.created_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Template Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Template</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Template Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
            />

            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={formData.category}
                label="Category"
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                <MenuItem value="general">General</MenuItem>
                <MenuItem value="promotion">Promotion</MenuItem>
                <MenuItem value="follow-up">Follow-up</MenuItem>
                <MenuItem value="cold-outreach">Cold Outreach</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Message Content"
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              multiline
              rows={6}
              fullWidth
              required
              helperText="Use spintax: {option1|option2|option3}. Variables: {name}, {username}"
            />

            <Alert severity="info">
              <Typography variant="caption">
                <strong>Spintax Example:</strong> Hello {'{bro|dude|friend}'}, this is a {'{test|demo}'} message!
              </Typography>
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
