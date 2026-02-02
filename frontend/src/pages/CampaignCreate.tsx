import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    Button,
    Card,
    CardContent,
    TextField,
    Typography,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Alert,
} from '@mui/material';
import { ArrowBack as BackIcon } from '@mui/icons-material';
import { TemplateSelector } from '../components/shared/TemplateSelector';
import api from '../api/Index';
import type { TelegramAccount, Template, CreateCampaignRequest } from '../Types/Index';
import toast from 'react-hot-toast';

export default function CampaignCreate() {
    const navigate = useNavigate();
    const [accounts, setAccounts] = useState<TelegramAccount[]>([]);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        telegram_account_id: 0,
        targets: '',
        min_delay: 5,
        max_delay: 10,
        daily_limit: '',
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchAccounts();
    }, []);

    const fetchAccounts = async () => {
        try {
            // Try /api/accounts/list first, fallback to /api/accounts/
            let response;
            try {
                response = await api.get('/api/accounts/list');
            } catch {
                response = await api.get('/api/accounts/');
            }
            setAccounts(response.data.filter((acc: TelegramAccount) => acc.status === 'active'));
        } catch (error: any) {
            console.error('Failed to fetch accounts:', error);
            toast.error('Failed to load accounts');
        }
    };

    const parseTargets = (targetsText: string) => {
        return targetsText
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                // If it's a number, treat as user_id, otherwise as username
                if (/^\d+$/.test(line)) {
                    return { user_id: line };
                } else {
                    return { username: line.replace('@', '') };
                }
            });
    };

    const handleSubmit = async () => {
        // Validation
        if (!formData.name) {
            toast.error('Campaign name is required');
            return;
        }
        if (!formData.telegram_account_id) {
            toast.error('Please select a Telegram account');
            return;
        }
        if (!selectedTemplate && !formData.targets) {
            toast.error('Please select a template or enter custom message');
            return;
        }
        if (!formData.targets) {
            toast.error('Please enter at least one target username or user ID');
            return;
        }
        if (formData.min_delay >= formData.max_delay) {
            toast.error('Min delay must be less than max delay');
            return;
        }

        const targets = parseTargets(formData.targets);
        if (targets.length === 0) {
            toast.error('No valid targets found');
            return;
        }

        const campaignData: any = {
            name: formData.name,
            telegram_account_id: formData.telegram_account_id,
            message_templates: selectedTemplate ? [selectedTemplate.content] : [],
            manual_targets: targets,
            min_delay: formData.min_delay,
            max_delay: formData.max_delay,
        };

        if (formData.daily_limit) {
            campaignData.daily_limit = parseInt(formData.daily_limit);
        }

        setLoading(true);
        try {
            const response = await api.post('/api/campaigns/', campaignData);
            toast.success('Campaign created successfully!');
            navigate(`/campaigns/${response.data.id}`);
        } catch (error: any) {
            console.error('Failed to create campaign:', error);
            toast.error(error.response?.data?.detail || 'Failed to create campaign');
        } finally {
            setLoading(false);
        }
    };

    const targetCount = parseTargets(formData.targets).length;

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3 }}>
                <Button
                    startIcon={<BackIcon />}
                    onClick={() => navigate('/campaigns')}
                    sx={{ mb: 2 }}
                >
                    Back to Campaigns
                </Button>
                <Typography variant="h4">Create New Campaign</Typography>
            </Box>

            <Card>
                <CardContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {/* Campaign Name */}
                        <TextField
                            label="Campaign Name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            required
                            fullWidth
                        />

                        {/* Account Selection */}
                        <FormControl fullWidth required>
                            <InputLabel>Telegram Account</InputLabel>
                            <Select
                                value={formData.telegram_account_id || ''}
                                label="Telegram Account"
                                onChange={(e) => setFormData({ ...formData, telegram_account_id: e.target.value as number })}
                            >
                                <MenuItem value="">
                                    <em>-- Select Account --</em>
                                </MenuItem>
                                {accounts.map(account => (
                                    <MenuItem key={account.id} value={account.id}>
                                        {account.nickname || account.phone_number} (Trust: {account.trust_score})
                                    </MenuItem>
                                ))}
                            </Select>
                            {accounts.length === 0 && (
                                <Alert severity="warning" sx={{ mt: 1 }}>
                                    No active accounts available. Please add and verify an account first.
                                </Alert>
                            )}
                        </FormControl>

                        {/* Template Selection */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                Message Template
                            </Typography>
                            <TemplateSelector
                                value={selectedTemplate?.id || null}
                                onChange={setSelectedTemplate}
                            />
                            {selectedTemplate && (
                                <Alert severity="info" sx={{ mt: 2 }}>
                                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                                        {selectedTemplate.content}
                                    </Typography>
                                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                        Spam Risk: {selectedTemplate.spam_risk_score.toFixed(0)}%
                                    </Typography>
                                </Alert>
                            )}
                        </Box>

                        {/* Targets Input */}
                        <Box>
                            <TextField
                                label="Target Users"
                                value={formData.targets}
                                onChange={(e) => setFormData({ ...formData, targets: e.target.value })}
                                multiline
                                rows={8}
                                fullWidth
                                required
                                placeholder="Enter one username or user ID per line&#10;Examples:&#10;johndoe&#10;@janedoe&#10;123456789"
                                helperText={`${targetCount} target${targetCount !== 1 ? 's' : ''} detected`}
                            />
                        </Box>

                        {/* Delay Settings */}
                        <Box sx={{ display: 'flex', gap: 2 }}>
                            <TextField
                                label="Min Delay (seconds)"
                                type="number"
                                value={formData.min_delay}
                                onChange={(e) => setFormData({ ...formData, min_delay: parseInt(e.target.value) || 0 })}
                                required
                                fullWidth
                                inputProps={{ min: 1 }}
                            />
                            <TextField
                                label="Max Delay (seconds)"
                                type="number"
                                value={formData.max_delay}
                                onChange={(e) => setFormData({ ...formData, max_delay: parseInt(e.target.value) || 0 })}
                                required
                                fullWidth
                                inputProps={{ min: 1 }}
                            />
                        </Box>

                        {/* Daily Limit */}
                        <TextField
                            label="Daily Message Limit (optional)"
                            type="number"
                            value={formData.daily_limit}
                            onChange={(e) => setFormData({ ...formData, daily_limit: e.target.value })}
                            fullWidth
                            helperText="Leave empty for no limit"
                            inputProps={{ min: 1 }}
                        />

                        {/* Submit Button */}
                        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                            <Button onClick={() => navigate('/campaigns')}>
                                Cancel
                            </Button>
                            <Button
                                variant="contained"
                                onClick={handleSubmit}
                                disabled={loading || accounts.length === 0}
                            >
                                {loading ? 'Creating...' : 'Create Campaign'}
                            </Button>
                        </Box>
                    </Box>
                </CardContent>
            </Card>
        </Box>
    );
}
