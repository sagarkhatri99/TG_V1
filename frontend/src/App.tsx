import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from '/src/theme/Index';
import Layout from '/src/components/layout/Layout';

// Pages
import Dashboard from '/src/pages/Dashboard';
import Accounts from '/src/pages/Accounts';
import ScrapeUsers from '/src/pages/ScrapeUsers';
import MonitorGroups from '/src/pages/MonitorGroups';
import MassDM from '/src/pages/MassDM';
import AutoPromo from '/src/pages/AutoPromo';
import Settings from '/src/pages/Settings';
import Help from '/src/pages/Help';
import Jobs from '/src/pages/Jobs';

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
              <Route path="/jobs" element={<Jobs />} />
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
