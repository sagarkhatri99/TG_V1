import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Button, TextField, Box, Typography, Stepper, Step, StepLabel, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const steps = ['Authentication', 'Verification', 'Run'];

const ScrapeStepper: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [phone, setPhone] = useState('');
  const [apiId, setApiId] = useState('');
  const [apiHash, setApiHash] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [group, setGroup] = useState('');

  const navigate = useNavigate();

  const authMutation = useMutation({
    mutationFn: (authData: any) => axios.post('/api/scrape/start-auth', authData),
    onSuccess: () => {
      setActiveStep((prevActiveStep) => prevActiveStep + 1);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (verifyData: any) => axios.post('/api/scrape/verify', verifyData),
    onSuccess: () => {
      setActiveStep((prevActiveStep) => prevActiveStep + 1);
    },
  });

  const runMutation = useMutation({
    mutationFn: (runData: any) => axios.post('/api/scrape/run', runData),
    onSuccess: () => {
      navigate('/jobs');
    },
  });

  const handleNext = () => {
    if (activeStep === 0) {
      authMutation.mutate({ phone_number: phone, api_id: apiId, api_hash: apiHash });
    } else if (activeStep === 1) {
      verifyMutation.mutate({ phone_number: phone, api_id: apiId, api_hash: apiHash, code, password });
    } else if (activeStep === 2) {
      runMutation.mutate({ phone_number: phone, api_id: apiId, api_hash: apiHash, group_username: group });
    }
  };

  return (
    <Box>
      <Stepper activeStep={activeStep}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {activeStep === 0 && (
        <Box>
          <TextField label="Phone Number" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth margin="normal" />
          <TextField label="API ID" value={apiId} onChange={(e) => setApiId(e.target.value)} fullWidth margin="normal" />
          <TextField label="API Hash" value={apiHash} onChange={(e) => setApiHash(e.target.value)} fullWidth margin="normal" />
        </Box>
      )}
      {activeStep === 1 && (
        <Box>
          <TextField label="Verification Code" value={code} onChange={(e) => setCode(e.target.value)} fullWidth margin="normal" />
          <TextField label="Password (if needed)" value={password} onChange={(e) => setPassword(e.target.value)} fullWidth margin="normal" />
        </Box>
      )}
      {activeStep === 2 && (
        <Box>
          <TextField label="Group Username" value={group} onChange={(e) => setGroup(e.target.value)} fullWidth margin="normal" />
        </Box>
      )}
      <Button onClick={handleNext}>{activeStep === steps.length - 1 ? 'Finish' : 'Next'}</Button>
      {authMutation.isError && <Alert severity="error">Authentication failed</Alert>}
      {verifyMutation.isError && <Alert severity="error">Verification failed</Alert>}
      {runMutation.isError && <Alert severity="error">Failed to start scraping job</Alert>}
    </Box>
  );
};

export default ScrapeStepper;