import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Button, Modal, Box, TextField, Typography } from '@mui/material';

const AddAccountForm: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState('');
  const [apiId, setApiId] = useState('');
  const [apiHash, setApiHash] = useState('');
  const [nickname, setNickname] = useState('');
  const [code, setCode] = useState('');
  const [verificationNeeded, setVerificationNeeded] = useState(false);
  const [accountId, setAccountId] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const addAccountMutation = useMutation({
    mutationFn: (newAccount: any) => axios.post('/api/accounts/add', newAccount),
    onSuccess: (data) => {
      setAccountId(data.data.account_id);
      setVerificationNeeded(true);
    },
  });

  const verifyAccountMutation = useMutation({
    mutationFn: (verificationData: any) => axios.post(`/api/accounts/verify/${accountId}`, verificationData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      setOpen(false);
    },
  });

  const handleSubmit = () => {
    addAccountMutation.mutate({ phone_number: phone, api_id: apiId, api_hash: apiHash, nickname });
  };

  const handleVerify = () => {
    verifyAccountMutation.mutate({ code });
  };

  return (
    <>
      <Button variant="contained" onClick={() => setOpen(true)}>Add Account</Button>
      <Modal open={open} onClose={() => setOpen(false)}>
        <Box sx={{ ...style }}>
          {!verificationNeeded ? (
            <>
              <Typography variant="h6">Add Account</Typography>
              <TextField label="Nickname" value={nickname} onChange={(e) => setNickname(e.target.value)} fullWidth margin="normal" />
              <TextField label="Phone Number" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth margin="normal" />
              <TextField label="API ID" value={apiId} onChange={(e) => setApiId(e.target.value)} fullWidth margin="normal" />
              <TextField label="API Hash" value={apiHash} onChange={(e) => setApiHash(e.target.value)} fullWidth margin="normal" />
              <Button onClick={handleSubmit}>Submit</Button>
            </>
          ) : (
            <>
              <Typography variant="h6">Verify Account</Typography>
              <TextField label="Verification Code" value={code} onChange={(e) => setCode(e.target.value)} fullWidth margin="normal" />
              <Button onClick={handleVerify}>Verify</Button>
            </>
          )}
        </Box>
      </Modal>
    </>
  );
};

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

export default AddAccountForm;