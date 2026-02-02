import React, { createContext, useState, useEffect, useContext } from 'react';



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
        if (token) {
            // Just mark as authenticated, don't fetch user profile
            // The user data was already returned from login or is not yet available
            setIsLoading(false);
        } else {
            setIsLoading(false);
        }
    }, [token]);

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
