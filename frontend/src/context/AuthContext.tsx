import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/Index';

interface User {
    id: number;
    email: string;
    subscription_plan: string;
}

interface AuthContextType {
    isAuthenticated: boolean;
    user: User | null;
    token: string | null;
    login: (token: string, userData?: User) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const initializeAuth = async () => {
            const storedToken = localStorage.getItem('token');
            if (!storedToken) {
                // No token — nothing to hydrate, just stop loading
                setIsLoading(false);
                return;
            }

            try {
                const response = await api.get('/api/auth/me');
                setUser(response.data as User);
            } catch {
                // Token is invalid or expired — clear it
                localStorage.removeItem('token');
                setToken(null);
                setUser(null);
            } finally {
                // Always runs: whether /me succeeded or failed
                setIsLoading(false);
            }
        };

        initializeAuth();
        // Run only once on mount
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const login = (newToken: string, userData?: User) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
        if (userData) {
            setUser(userData);
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
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
