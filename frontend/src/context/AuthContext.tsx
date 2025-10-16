import React, { createContext, useState, useEffect, useContext } from 'react';
import Cookies from 'js-cookie';
import axiosInstance from '../api/axios';

interface User {
    id: number;
    email: string;
    subscription_plan: string;
    status: string;
}

interface AuthContextType {
    isAuthenticated: boolean;
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [token, setToken] = useState<string | null>(localStorage.getItem('token') || Cookies.get('access_token'));
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            if (token) {
                try {
                    const response = await axiosInstance.get('/auth/verify');
                    setUser(response.data);
                } catch (error) {
                    console.error('Failed to fetch user', error);
                    localStorage.removeItem('token');
                    Cookies.remove('access_token');
                    setToken(null);
                    setUser(null);
                    window.location.href = 'https://ogtools.shop/login';
                }
            }
            setIsLoading(false);
        };

        fetchUser();
    }, [token]);

    const login = (newToken: string) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
    };

    const logout = () => {
        localStorage.removeItem('token');
        Cookies.remove('access_token');
        setToken(null);
        setUser(null);
        window.location.href = 'https://ogtools.shop/login';
    };

    return (
        <AuthContext.Provider
            value={{
                isAuthenticated: !!token,
                user,
                token,
                login,
                logout,
                isLoading,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
