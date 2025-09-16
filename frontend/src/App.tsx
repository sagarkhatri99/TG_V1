import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from './theme/index';
import Layout from './components/layout/Layout';

// Pages
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import ScrapeUsers from './pages/ScrapeUsers';
import MonitorGroups from './pages/MonitorGroups';
import MassDM from './pages/MassDM';
import AutoPromo from './pages/AutoPromo';
import Settings from './pages/Settings';
import Help from './pages/Help';
import Jobs from './pages/Jobs';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import Proxies from './pages/Proxies';

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/scrape" element={<ScrapeUsers />} />
        <Route path="/monitor" element={<MonitorGroups />} />
        <Route path="/mass-dm" element={<MassDM />} />
        <Route path="/auto-promo" element={<AutoPromo />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
        <Route path="/proxies" element={<Proxies />} />
      </Route>
    </Routes>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
