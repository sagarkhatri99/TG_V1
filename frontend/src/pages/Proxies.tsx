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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Science as TestIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import api from '../api/Index';
import type { Proxy } from '../Types/Index';

export default function Proxies() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [formData, setFormData] = useState({ proxy_url: '', name: '' });
  const [testingProxies, setTestingProxies] = useState<{ [key: number]: boolean }>({});

  // Rename dialog state
  const [renameDialog, setRenameDialog] = useState<{ open: boolean; proxyId: number | null; currentName: string }>({
    open: false,
    proxyId: null,
    currentName: '',
  });
  const [renameName, setRenameName] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);

  const fetchProxies = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/proxies/list');
      setProxies(response.data);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to fetch proxies.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProxies();
  }, []);

  const handleCreateProxy = async () => {
    if (!formData.proxy_url.trim()) return;
    setLoading(true);
    try {
      await api.post('/api/proxies/create', {
        proxy_url: formData.proxy_url,
        name: formData.name.trim() || undefined,
      });
      setAlert({ type: 'success', message: 'Proxy added successfully!' });
      setFormData({ proxy_url: '', name: '' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to add proxy.' });
    } finally {
      setLoading(false);
    }
  };

  const handleTestProxy = async (proxyId: number) => {
    setTestingProxies((prev) => ({ ...prev, [proxyId]: true }));
    try {
      const response = await api.post(`/api/proxies/${proxyId}/test`);
      setAlert({
        type: 'success',
        message: `Proxy test successful! IP: ${response.data.ip_address}, Response time: ${response.data.response_time}ms`,
      });
      fetchProxies();
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.response?.data?.detail || 'Proxy test failed.',
      });
      fetchProxies();
    } finally {
      setTestingProxies((prev) => {
        const newState = { ...prev };
        delete newState[proxyId];
        return newState;
      });
    }
  };

  const handleDeleteProxy = async (id: number) => {
    if (!confirm('Are you sure you want to delete this proxy?')) return;
    try {
      await api.delete(`/api/proxies/${id}`);
      setAlert({ type: 'success', message: 'Proxy deleted successfully!' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to delete proxy.' });
    }
  };

  const openRenameDialog = (proxy: Proxy) => {
    setRenameDialog({ open: true, proxyId: proxy.id, currentName: proxy.name || '' });
    setRenameName(proxy.name || '');
  };

  const handleRenameProxy = async () => {
    if (!renameDialog.proxyId || !renameName.trim()) return;
    setRenameLoading(true);
    try {
      await api.put(`/api/proxies/${renameDialog.proxyId}/rename`, { name: renameName.trim() });
      setAlert({ type: 'success', message: `Proxy renamed to "${renameName.trim()}"` });
      setRenameDialog({ open: false, proxyId: null, currentName: '' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to rename proxy.' });
    } finally {
      setRenameLoading(false);
    }
  };

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'active': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getDisplayName = (proxy: Proxy) =>
    proxy.name ? proxy.name : <Typography component="span" variant="body2" color="text.secondary">Proxy #{proxy.id}</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="h4">Proxy Management</Typography>
        <Button
          variant="outlined"
          startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          onClick={fetchProxies}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Add, test, rename, and manage your SOCKS5 proxies. All proxies are enforced as SOCKS5.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Add New Proxy</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <TextField
              label="Proxy URL"
              placeholder="socks5://username:password@host:port"
              value={formData.proxy_url}
              onChange={(e) => setFormData({ ...formData, proxy_url: e.target.value })}
              sx={{ flex: 2, minWidth: 280 }}
            />
            <TextField
              label="Label (optional)"
              placeholder='e.g. "US Residential 1"'
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              sx={{ flex: 1, minWidth: 180 }}
            />
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateProxy}
              disabled={loading || !formData.proxy_url}
              sx={{ height: 56 }}
            >
              Add
            </Button>
          </Box>
        </CardContent>
      </Card>

      {alert && (
        <Alert severity={alert.type} onClose={() => setAlert(null)} sx={{ mb: 3 }}>
          {alert.message}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Label</TableCell>
                <TableCell>Proxy URL</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Response Time</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {proxies.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary">No proxies added yet</Typography>
                  </TableCell>
                </TableRow>
              )}
              {proxies.map((proxy) => (
                <TableRow key={proxy.id}>
                  <TableCell>{proxy.id}</TableCell>
                  <TableCell>
                    <Box fontWeight={proxy.name ? 'bold' : 'normal'}>
                      {getDisplayName(proxy)}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      title={proxy.proxy_url}
                    >
                      {proxy.proxy_url}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={proxy.proxy_type.toUpperCase()} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip label={proxy.status} color={getStatusColor(proxy.status)} size="small" />
                  </TableCell>
                  <TableCell>
                    {proxy.ip_address ? (
                      <Typography variant="body2" fontFamily="monospace">
                        {proxy.ip_address}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Not tested
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {proxy.response_time ? (
                      <Chip
                        label={`${proxy.response_time}ms`}
                        size="small"
                        color={proxy.response_time < 1000 ? 'success' : proxy.response_time < 3000 ? 'warning' : 'error'}
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={0.5}>
                      <Tooltip title="Rename / Set Label">
                        <IconButton onClick={() => openRenameDialog(proxy)} color="default" size="small">
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Test Connection">
                        <IconButton
                          onClick={() => handleTestProxy(proxy.id)}
                          color="primary"
                          size="small"
                          disabled={testingProxies[proxy.id]}
                        >
                          {testingProxies[proxy.id] ? <CircularProgress size={18} /> : <TestIcon fontSize="small" />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Proxy">
                        <IconButton
                          onClick={() => handleDeleteProxy(proxy.id)}
                          color="error"
                          size="small"
                          disabled={testingProxies[proxy.id]}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Rename Dialog */}
      <Dialog
        open={renameDialog.open}
        onClose={() => setRenameDialog({ open: false, proxyId: null, currentName: '' })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Rename Proxy #{renameDialog.proxyId}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Label / Name"
            placeholder='e.g. "US Residential 1" or "Germany VPS"'
            value={renameName}
            onChange={(e) => setRenameName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRenameProxy()}
            sx={{ mt: 1 }}
            helperText="This label is only for your convenience — it is not sent to Telegram."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialog({ open: false, proxyId: null, currentName: '' })}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleRenameProxy}
            disabled={renameLoading || !renameName.trim()}
          >
            {renameLoading ? <CircularProgress size={20} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
