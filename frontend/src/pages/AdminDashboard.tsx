import { Box, Alert } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { AdminDashboardContent } from '../components/AdminDashboardContent';

export default function AdminDashboard() {
  const { user: currentUser } = useAuth();

  if (currentUser?.subscription_plan !== 'admin') {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <Alert severity="error">
          Access denied. Admin privileges required.
        </Alert>
      </Box>
    );
  }

  return <AdminDashboardContent />;
}
