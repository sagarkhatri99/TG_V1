import React, { useState } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    TextField,
    Button,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Alert,
    CircularProgress,
    List,
    ListItem,
    ListItemText,
} from '@mui/material';
import { CloudUpload as UploadIcon, GroupAdd as GroupAddIcon } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import api from '../api/Index';
import type { TelegramAccount } from '../Types/Index';
import { useNavigate } from 'react-router-dom';

export default function GroupJoiner() {
    const navigate = useNavigate();
    const [selectedAccount, setSelectedAccount] = useState<string>('');
    const [description, setDescription] = useState('');
    const [minDelay, setMinDelay] = useState<number>(30);
    const [maxDelay, setMaxDelay] = useState<number>(60);
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [alert, setAlert] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
    const [preview, setPreview] = useState<{ count: number; items: string[] } | null>(null);

    const { data: accounts = [], isLoading: accountsLoading } = useQuery<TelegramAccount[]>({
        queryKey: ['accounts'],
        queryFn: async () => {
            const response = await api.get('/api/accounts/list');
            return response.data;
        },
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
        }
    };

    const handleDownloadTemplate = () => {
        const content = "group_link\nhttps://t.me/example_group\n@another_group";
        const blob = new Blob([content], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'group_joiner_template.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedAccount || !file) {
            setAlert({ type: 'error', message: 'Please select an account and upload a CSV file' });
            return;
        }

        setLoading(true);
        setAlert(null);
        setPreview(null);

        const formData = new FormData();
        formData.append('account_id', selectedAccount);
        formData.append('csv_file', file);
        formData.append('min_delay_seconds', minDelay.toString());
        formData.append('max_delay_seconds', maxDelay.toString());
        if (description) formData.append('user_description', description);

        try {
            const response = await api.post('/api/group-joiner/create-job', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setAlert({ type: 'success', message: response.data.message });
            setPreview({
                count: response.data.groups_count,
                items: response.data.groups_preview,
            });

            // Reset form on success
            setFile(null);
            setDescription('');

            // Optionally redirect to jobs page after a short delay
            setTimeout(() => {
                navigate('/jobs');
            }, 3000);

        } catch (error: any) {
            console.error('Job creation error:', error);
            setAlert({
                type: 'error',
                message: error.response?.data?.detail || 'An error occurred while creating the job.'
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box sx={{ maxWidth: 800, mx: 'auto', p: 2 }}>
            <Typography variant="h4" gutterBottom>
                Group Joiner
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Upload a CSV file containing Telegram group links or usernames, and choose an account to automatically join them.
            </Typography>

            <Card sx={{ mt: 3 }}>
                <CardContent>
                    <form onSubmit={handleSubmit}>
                        <FormControl fullWidth margin="normal" required>
                            <InputLabel>Select Sending Account</InputLabel>
                            <Select
                                value={selectedAccount}
                                label="Select Sending Account"
                                onChange={(e) => setSelectedAccount(e.target.value)}
                                disabled={accountsLoading}
                            >
                                {accounts.filter(a => a.status === 'active').map((account) => (
                                    <MenuItem key={account.id} value={account.id.toString()}>
                                        {account.phone_number} {account.nickname ? `(${account.nickname})` : ''}
                                    </MenuItem>
                                ))}
                                {accounts.filter(a => a.status === 'active').length === 0 && (
                                    <MenuItem disabled value="">
                                        No active accounts available
                                    </MenuItem>
                                )}
                            </Select>
                        </FormControl>

                        <TextField
                            margin="normal"
                            fullWidth
                            label="Job Description (Optional)"
                            placeholder="e.g., Joining crypto groups batch 1"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            helperText="For your reference in the Jobs list"
                        />

                        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                            <TextField
                                fullWidth
                                type="number"
                                label="Min Delay (Seconds)"
                                value={minDelay}
                                onChange={(e) => setMinDelay(Number(e.target.value) || 10)}
                                InputProps={{ inputProps: { min: 10 } }}
                                helperText="Minimum gap between joins"
                            />
                            <TextField
                                fullWidth
                                type="number"
                                label="Max Delay (Seconds)"
                                value={maxDelay}
                                onChange={(e) => setMaxDelay(Number(e.target.value) || 60)}
                                InputProps={{ inputProps: { min: 10 } }}
                                helperText="Maximum gap between joins"
                            />
                        </Box>

                        <Box sx={{ mt: 3, mb: 2, p: 2, border: '1px dashed grey', borderRadius: 1, backgroundColor: 'background.default' }}>
                            <Typography variant="subtitle1" gutterBottom>
                                Upload Group List (CSV)
                            </Typography>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography variant="body2" color="text.secondary">
                                    The CSV must contain a column named <strong>group_link</strong>, <strong>group_url</strong>, <strong>username</strong>, or <strong>link</strong>.<br />
                                    It can contain full URLs (https://t.me/groupname) or just the @username.
                                </Typography>
                                <Button variant="text" size="small" onClick={handleDownloadTemplate}>
                                    Download Template
                                </Button>
                            </Box>
                            <Button
                                variant="outlined"
                                component="label"
                                startIcon={<UploadIcon />}
                                fullWidth
                            >
                                {file ? file.name : 'Select CSV File'}
                                <input
                                    type="file"
                                    hidden
                                    accept=".csv"
                                    onChange={handleFileChange}
                                />
                            </Button>
                        </Box>

                        {alert && (
                            <Alert severity={alert.type} sx={{ mt: 2, mb: 2 }}>
                                {alert.message}
                            </Alert>
                        )}

                        {preview && (
                            <Alert severity="info" sx={{ mt: 2, mb: 2, '& .MuiAlert-message': { width: '100%' } }}>
                                <Typography variant="subtitle2" gutterBottom>
                                    Found {preview.count} groups to join. Here's a preview:
                                </Typography>
                                <List dense disablePadding>
                                    {preview.items.map((item, idx) => (
                                        <ListItem key={idx} disableGutters sx={{ py: 0 }}>
                                            <ListItemText primary={item} />
                                        </ListItem>
                                    ))}
                                    {preview.count > preview.items.length && (
                                        <ListItem disableGutters sx={{ py: 0 }}>
                                            <ListItemText primary="..." />
                                        </ListItem>
                                    )}
                                </List>
                                <Typography variant="body2" sx={{ mt: 1 }}>
                                    Redirecting to Jobs dashboard in 3 seconds...
                                </Typography>
                            </Alert>
                        )}

                        <Button
                            type="submit"
                            variant="contained"
                            color="primary"
                            size="large"
                            fullWidth
                            disabled={loading || !selectedAccount || !file}
                            startIcon={loading ? <CircularProgress size={24} color="inherit" /> : <GroupAddIcon />}
                            sx={{ mt: 2 }}
                        >
                            {loading ? 'Creating Job...' : 'Start Group Joiner'}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </Box>
    );
}
