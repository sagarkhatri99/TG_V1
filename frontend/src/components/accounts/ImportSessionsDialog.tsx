import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  Select,
  MenuItem,
  IconButton,
  Chip,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import api from '../../api/Index';
import type { Proxy } from '../../Types/Index';
import toast from 'react-hot-toast';

interface ImportSessionsDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface SessionPair {
  basename: string;
  sessionFile: File | null;
  jsonFile: File | null;
  proxyId: number | '';
  status: 'pending' | 'valid' | 'invalid';
  error?: string;
}

export const ImportSessionsDialog: React.FC<ImportSessionsDialogProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const [sessionPairs, setSessionPairs] = useState<SessionPair[]>([]);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchProxies();
    }
  }, [open]);

  const fetchProxies = async () => {
    try {
      const response = await api.get('/api/proxies/list');
      setProxies(response.data || []);
    } catch (error) {
      console.error('Failed to fetch proxies', error);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files) return;

    const files = Array.from(event.target.files);
    const newPairs: { [key: string]: SessionPair } = {};

    // Group files by basename
    files.forEach(file => {
      const isSession = file.name.endsWith('.session');
      const isJson = file.name.endsWith('.json');

      if (!isSession && !isJson) return;

      const basename = file.name.replace(/\.(session|json)$/, '');

      if (!newPairs[basename]) {
        newPairs[basename] = {
          basename,
          sessionFile: null,
          jsonFile: null,
          proxyId: '',
          status: 'pending',
        };
      }

      if (isSession) {
        newPairs[basename].sessionFile = file;
      } else if (isJson) {
        newPairs[basename].jsonFile = file;
      }
    });

    // Validate pairs
    Object.values(newPairs).forEach(pair => {
      if (!pair.sessionFile) {
        pair.status = 'invalid';
        pair.error = 'Missing .session file';
      } else if (!pair.jsonFile) {
        pair.status = 'invalid';
        pair.error = 'Missing .json metadata file';
      } else {
        pair.status = 'valid';
      }
    });

    setSessionPairs(Object.values(newPairs));
    setError(null);
  };

  const handleProxyChange = (basename: string, proxyId: number | '') => {
    setSessionPairs(prev =>
      prev.map(pair =>
        pair.basename === basename ? { ...pair, proxyId } : pair
      )
    );
  };

  const handleRemovePair = (basename: string) => {
    setSessionPairs(prev => prev.filter(pair => pair.basename !== basename));
  };

  const handleUpload = async () => {
    const validPairs = sessionPairs.filter(pair => pair.status === 'valid');

    if (validPairs.length === 0) {
      setError('No valid session pairs to import. Each account needs both .session and .json files.');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();

    // Add all session and json files
    validPairs.forEach(pair => {
      if (pair.sessionFile) formData.append('files', pair.sessionFile);
      if (pair.jsonFile) formData.append('files', pair.jsonFile);
    });

    // Add proxy mappings as JSON
    const proxyMappings: { [key: string]: number | null } = {};
    validPairs.forEach(pair => {
      if (pair.proxyId) {
        proxyMappings[pair.basename] = Number(pair.proxyId);
      }
    });

    if (Object.keys(proxyMappings).length > 0) {
      formData.append('proxy_mappings', JSON.stringify(proxyMappings));
    }

    try {
      const response = await api.post('/api/accounts/import-sessions', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const result = response.data;

      if (result.summary.imported > 0) {
        toast.success(`Successfully imported ${result.summary.imported} account(s)`);

        if (result.errors && result.errors.length > 0) {
          toast.error(`${result.errors.length} account(s) failed to import`);
        }

        onSuccess();
        handleClose();
      } else {
        setError('Import failed. Check console for details.');
        console.error('Import errors:', result.errors);
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to import sessions. Please check file formats.';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setSessionPairs([]);
      setError(null);
      onClose();
    }
  };

  const validCount = sessionPairs.filter(p => p.status === 'valid').length;
  const invalidCount = sessionPairs.filter(p => p.status === 'invalid').length;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Import Telegram Sessions</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Import accounts using .session and .json file pairs. Files are matched by name.
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Example: <code>phone.session</code> + <code>phone.json</code>
          </Typography>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="caption">
            <strong>JSON file must contain:</strong> <code>app_id</code>, <code>app_hash</code>, <code>phone</code>
          </Typography>
        </Alert>

        <Button
          variant="outlined"
          component="label"
          startIcon={<UploadIcon />}
          fullWidth
          sx={{ mb: 2 }}
          disabled={uploading}
        >
          Select Session Files (.session + .json)
          <input
            type="file"
            multiple
            accept=".session,.json"
            hidden
            onChange={handleFileSelect}
          />
        </Button>

        {sessionPairs.length > 0 && (
          <>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Chip
                label={`${validCount} Valid`}
                color="success"
                size="small"
                icon={<CheckIcon />}
              />
              {invalidCount > 0 && (
                <Chip
                  label={`${invalidCount} Invalid`}
                  color="error"
                  size="small"
                  icon={<ErrorIcon />}
                />
              )}
            </Box>

            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Account</TableCell>
                    <TableCell>Files</TableCell>
                    <TableCell>Proxy (Optional)</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell width={50}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sessionPairs.map((pair) => (
                    <TableRow key={pair.basename}>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {pair.basename}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" display="block">
                          {pair.sessionFile ? '✓ .session' : '✗ .session'}
                        </Typography>
                        <Typography variant="caption" display="block">
                          {pair.jsonFile ? '✓ .json' : '✗ .json'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <FormControl size="small" fullWidth disabled={pair.status === 'invalid'}>
                          <Select
                            value={pair.proxyId}
                            onChange={(e) => handleProxyChange(pair.basename, e.target.value as number | '')}
                            displayEmpty
                          >
                            <MenuItem value="">
                              <em>None</em>
                            </MenuItem>
                            {proxies.map((proxy) => (
                              <MenuItem key={proxy.id} value={proxy.id}>
                                {proxy.proxy_url}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </TableCell>
                      <TableCell>
                        {pair.status === 'valid' ? (
                          <Chip label="Ready" color="success" size="small" />
                        ) : (
                          <Chip label={pair.error || 'Invalid'} color="error" size="small" />
                        )}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleRemovePair(pair.basename)}
                          disabled={uploading}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}

        {uploading && <LinearProgress sx={{ mt: 2 }} />}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={validCount === 0 || uploading}
        >
          {uploading ? 'Importing...' : `Import ${validCount} Account(s)`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
