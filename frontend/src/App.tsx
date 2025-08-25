import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from './theme';
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/scrape" element={<ScrapeUsers />} />
              <Route path="/monitor" element={<MonitorGroups />} />
              <Route path="/mass-dm" element={<MassDM />} />
              <Route path="/auto-promo" element={<AutoPromo />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/help" element={<Help />} />
            </Routes>
          </Layout>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
