import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Button, TextField, Box, Typography, Alert } from '@mui/material';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';

const MassDMBotForm: React.FC = () => {
  const [botToken, setBotToken] = useState('');
  const [message, setMessage] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: (newJob: FormData) => axios.post('/api/dm/bot/create', newJob),
    onSuccess: () => {
      navigate('/jobs');
    },
  });

  const onDrop = (acceptedFiles: File[]) => {
    setCsvFile(acceptedFiles[0]);
  };

  const { getRootProps, getInputProps } = useDropzone({ onDrop, accept: { 'text/csv': ['.csv'] } });

  const handleSubmit = () => {
    if (!csvFile) return;
    const formData = new FormData();
    formData.append('bot_token', botToken);
    formData.append('message', message);
    formData.append('csv_file', csvFile);
    mutation.mutate(formData);
  };

  return (
    <Box>
      <Typography variant="h6">Mass DM (Bot Mode)</Typography>
      <TextField label="Bot Token" value={botToken} onChange={(e) => setBotToken(e.target.value)} fullWidth margin="normal" />
      <TextField label="Message" value={message} onChange={(e) => setMessage(e.target.value)} fullWidth multiline rows={4} margin="normal" />
      <Box {...getRootProps()} sx={{ border: '2px dashed grey', p: 2, mt: 2, textAlign: 'center' }}>
        <input {...getInputProps()} />
        <p>Drag 'n' drop a CSV file here, or click to select one</p>
        {csvFile && <p>{csvFile.name}</p>}
      </Box>
      <Button onClick={handleSubmit} sx={{ mt: 2 }}>Submit</Button>
      {mutation.isError && <Alert severity="error">Error creating job</Alert>}
    </Box>
  );
};

export default MassDMBotForm;