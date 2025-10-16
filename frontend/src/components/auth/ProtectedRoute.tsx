import React, { useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Box, CircularProgress, Modal, Typography, Button } from '@mui/material';
import Layout from '../layout/Layout';

const ProtectedRoute: React.FC = () => {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();
    const [open, setOpen] = useState(true);

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    if (!isAuthenticated) {
        const returnUrl = encodeURIComponent(location.pathname + location.search);
        return <Navigate to={`https://ogtools.shop/login?return_url=${returnUrl}`} replace />;
    }

    if (user?.status === 'expired') {
        return (
            <Modal open={open} onClose={() => setOpen(false)}>
                <Box sx={{ ...style }}>
                    <Typography variant="h6">Trial Expired</Typography>
                    <Typography>Your trial has expired. Please upgrade to continue.</Typography>
                    <Button onClick={() => window.location.href = 'https://ogtools.shop/contact'}>Contact Us</Button>
                </Box>
            </Modal>
        );
    }

    return (
        <Layout>
            <Outlet />
        </Layout>
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

export default ProtectedRoute;
