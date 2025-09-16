import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from './theme/Index';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import ScrapeUsers from './pages/ScrapeUsers';
import MonitorGroups from './pages/MonitorGroups';
import MassDM from './pages/MassDM';
import AutoPromo from './pages/AutoPromo';
import Settings from './pages/Settings';
import Help from './pages/Help';
import Jobs from './pages/Jobs';
import Proxies from './pages/Proxies';
import Layout from './components/layout/Layout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/jobs" element={<Layout><Jobs /></Layout>} />
        <Route path="/accounts" element={<Layout><Accounts /></Layout>} />
        <Route path="/scrape" element={<Layout><ScrapeUsers /></Layout>} />
        <Route path="/monitor" element={<Layout><MonitorGroups /></Layout>} />
        <Route path="/mass-dm" element={<Layout><MassDM /></Layout>} />
        <Route path="/auto-promo" element={<Layout><AutoPromo /></Layout>} />
        <Route path="/settings" element={<Layout><Settings /></Layout>} />
        <Route path="/help" element={<Layout><Help /></Layout>} />
        <Route path="/proxies" element={<Layout><Proxies /></Layout>} />
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