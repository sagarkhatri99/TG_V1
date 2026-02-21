import React, { useState } from 'react';
import { Container, TextField, Button, Typography, Box, Link } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import api from '../api/Index';

const LoginPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        console.log('Login attempt:', email);

        try {
            const response = await api.post('/api/auth/login', {
                username: email,
                password: password,
            });

            console.log('Login success:', response.data);

            const token = response.data.token || response.data.access_token;
            if (token) {
                login(token, response.data.user);
                if (response.data.user.subscription_plan === 'admin') {
                    navigate('/admin');
                } else {
                    navigate('/');
                }
            } else {
                throw new Error('No token received from server');
            }

        } catch (err: any) {
            console.error('Login error:', err);

            let message = 'An unexpected error occurred. Please try again.';

            if (axios.isAxiosError(err)) {
                if (err.response) {
                    message = err.response.data?.detail || err.response.data?.message || `Error ${err.response.status}: ${err.response.statusText}`;
                } else if (err.request) {
                    message = 'No response from server. Please check if the backend is running.';
                } else {
                    message = err.message;
                }
            } else if (err instanceof Error) {
                message = err.message;
            }

            setError(message);
        }
    };

    return (
        <Container maxWidth="xs">
            <Box
                sx={{
                    marginTop: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                }}
            >
                <Typography component="h1" variant="h5">
                    Sign in
                </Typography>
                <Box component="form" onSubmit={handleLogin} sx={{ mt: 1 }} noValidate>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="email"
                        label="Email Address"
                        name="email"
                        autoComplete="off"
                        autoFocus
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        inputProps={{ type: 'text' }}
                    />
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        name="password"
                        label="Password"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    {error && (
                        <Typography color="error" align="center" sx={{ mt: 2 }}>
                            {error}
                        </Typography>
                    )}
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                    >
                        Sign In
                    </Button>
                    <Box sx={{ textAlign: 'center', mt: 2 }}>
                        <Link href="/register" variant="body2">
                            {"Don't have an account? Sign Up"}
                        </Link>
                    </Box>
                </Box>
            </Box>
        </Container>
    );
};

export default LoginPage;