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
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import api from '../api/Index';

interface Proxy {
  id: number;
  proxy_url: string;
  proxy_type: string;
  country_code: string;
  status: string;
}

export default function Proxies() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [formData, setFormData] = useState({ proxy_url: '', proxy_type: 'http' });

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

  const handleDeleteProxy = async (id: number) => {
    try {
      await api.delete(`/api/proxies/${id}`);
      setAlert({ type: 'success', message: 'Proxy deleted successfully!' });
      fetchProxies();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to delete proxy.' });
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Proxy Management
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Add, view, and manage your proxies.
      </Typography>

      <Card sx={{ mt: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Add New Proxy</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              fullWidth
              label="Proxy URL (e.g., http://user:pass@host:port)"
              value={formData.proxy_url}
              onChange={(e) => setFormData({ ...formData, proxy_url: e.target.value })}
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
        <CircularProgress />
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Proxy URL</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {proxies.map((proxy) => (
                <TableRow key={proxy.id}>
                  <TableCell>{proxy.id}</TableCell>
                  <TableCell>{proxy.proxy_url}</TableCell>
                  <TableCell>{proxy.proxy_type}</TableCell>
                  <TableCell>{proxy.status}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleDeleteProxy(proxy.id)} color="error">
                      <DeleteIcon />
                    </IconButton>
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
