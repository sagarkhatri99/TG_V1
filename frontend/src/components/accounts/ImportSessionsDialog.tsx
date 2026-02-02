import React, { useState } from 'react';
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
} from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';
import api from '../../api/Index';

interface ImportSessionsDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImportSessionsDialog: React.FC<ImportSessionsDialogProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!files || files.length === 0) {
      setError('Please select at least one .session file');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    try {
      await api.post('/api/accounts/import-sessions', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      onSuccess();
      onClose();
      setFiles(null);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to import sessions. Please check file format.');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles(null);
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Import Telegram Session Files</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ my: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Select .session files from your device. You can select multiple files at once.
          </Typography>

          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadIcon />}
            fullWidth
            sx={{ mt: 2 }}
            disabled={uploading}
          >
            Choose Files
            <input
              type="file"
              multiple
              accept=".session"
              hidden
              onChange={(e) => setFiles(e.target.files)}
            />
          </Button>

          {files && files.length > 0 && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: {files.length} file(s)
            </Typography>
          )}
        </Box>

        {uploading && <LinearProgress sx={{ mt: 2 }} />}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={!files || uploading}
        >
          {uploading ? 'Uploading...' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
