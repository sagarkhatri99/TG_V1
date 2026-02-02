import { useState, useEffect } from 'react';
import {
    Box,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Typography,
    CircularProgress,
    Alert,
    Paper,
} from '@mui/material';
import api from '../../api/Index';

export interface Template {
    id: number;
    name: string;
    content: string;
    category: string;
    spam_risk_score: number;
    variables: string[];
    created_at: string;
}

interface TemplateSelectorProps {
    selectedTemplateId?: number | null;
    onSelect: (template: Template | null) => void;
}

export default function TemplateSelector({ selectedTemplateId, onSelect }: TemplateSelectorProps) {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchTemplates();
    }, []);

    const fetchTemplates = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/api/templates');
            setTemplates(response.data || []);
        } catch (err: any) {
            console.error('Failed to fetch templates:', err);
            setError(err.response?.data?.detail || 'Failed to load templates');
            setTemplates([]);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (value: string) => {
        if (value === 'custom') {
            onSelect(null);
        } else {
            const templateId = parseInt(value);
            const template = templates.find(t => t.id === templateId);
            onSelect(template || null);
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CircularProgress size={24} />
                <Typography variant="body2" color="text.secondary">
                    Loading templates...
                </Typography>
            </Box>
        );
    }

    if (error) {
        return (
            <Alert severity="error" sx={{ mb: 2 }}>
                {error}
            </Alert>
        );
    }

    const selectedTemplate = templates.find(t => t.id === selectedTemplateId);

    return (
        <Box>
            <FormControl fullWidth>
                <InputLabel>Message Template</InputLabel>
                <Select
                    value={selectedTemplateId ? selectedTemplateId.toString() : 'custom'}
                    onChange={(e) => handleChange(e.target.value)}
                    label="Message Template"
                >
                    <MenuItem value="custom">
                        <em>Use custom message</em>
                    </MenuItem>
                    {templates.map((template) => (
                        <MenuItem key={template.id} value={template.id.toString()}>
                            {template.name}
                            {template.spam_risk_score > 50 && (
                                <Typography
                                    component="span"
                                    variant="caption"
                                    color="warning.main"
                                    sx={{ ml: 1 }}
                                >
                                    (High spam risk)
                                </Typography>
                            )}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>

            {selectedTemplate && (
                <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50' }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Template Preview:
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {selectedTemplate.content}
                    </Typography>
                    {selectedTemplate.variables && selectedTemplate.variables.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                                Variables: {selectedTemplate.variables.join(', ')}
                            </Typography>
                        </Box>
                    )}
                </Paper>
            )}

            {templates.length === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                    No templates found. Create one in the Templates page first.
                </Alert>
            )}
        </Box>
    );
}
