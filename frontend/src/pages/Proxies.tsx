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
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Science as TestIcon } from '@mui/icons-material';
import api from '../api/Index';
import type { Proxy } from '../Types/Index';

export default function Proxies() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [formData, setFormData] = useState({ proxy_url: '', proxy_type: 'http' });
  const [testingProxies, setTestingProxies] = useState<{ [key: number]: boolean }>({});

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
    setLoading(true);
    try {
      await api.post('/api/proxies/create', formData);
      setAlert({ type: 'success', message: 'Proxy added successfully!' });
      setFormData({ proxy_url: '', proxy_type: 'http' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to add proxy.' });
    } finally {
      setLoading(false);
    }
  };

  const handleTestProxy = async (proxyId: number) => {
    setTestingProxies(prev => ({ ...prev, [proxyId]: true }));
    try {
      const response = await api.post(`/api/proxies/${proxyId}/test`);
      setAlert({
        type: 'success',
        message: `Proxy test successful! IP: ${response.data.ip_address}, Response time: ${response.data.response_time}ms`
      });
      fetchProxies(); // Refresh to show updated IP and status
    } catch (error: any) {
      setAlert({
        type: 'error',
        message: error.response?.data?.detail || 'Proxy test failed.'
      });
      fetchProxies(); // Refresh to show failed status
    } finally {
      setTestingProxies(prev => {
        const newState = { ...prev };
        delete newState[proxyId];
        return newState;
      });
    }
  };

  const handleDeleteProxy = async (id: number) => {
    if (!confirm('Are you sure you want to delete this proxy?')) {
      return;
    }

    try {
      await api.delete(`/api/proxies/${id}`);
      setAlert({ type: 'success', message: 'Proxy deleted successfully!' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to delete proxy.' });
    }
  };

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'active': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Proxy Management
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Add, test, and manage your proxies. IProyal proxies are supported.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Add New Proxy</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              fullWidth
              label="Proxy URL (e.g., http://user:pass@host:port or socks5://user:pass@host:port)"
              value={formData.proxy_url}
              onChange={(e) => setFormData({ ...formData, proxy_url: e.target.value })}
              placeholder="http://username:password@proxy.iproyal.com:12321"
            />
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateProxy}
              disabled={loading || !formData.proxy_url}
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
                <TableCell>Proxy URL</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Response Time</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {proxies.map((proxy) => (
                <TableRow key={proxy.id}>
                  <TableCell>{proxy.id}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {proxy.proxy_url}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={proxy.proxy_type.toUpperCase()} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={proxy.status}
                      color={getStatusColor(proxy.status)}
                      size="small"
                    />
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
                      <Typography variant="body2" color="text.secondary">
                        -
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Tooltip title="Test Connection">
                        <IconButton
                          onClick={() => handleTestProxy(proxy.id)}
                          color="primary"
                          disabled={testingProxies[proxy.id]}
                        >
                          {testingProxies[proxy.id] ? <CircularProgress size={20} /> : <TestIcon />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Proxy">
                        <IconButton
                          onClick={() => handleDeleteProxy(proxy.id)}
                          color="error"
                          disabled={testingProxies[proxy.id]}
                        >
                          <DeleteIcon />
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
    </Box>
  );
}
