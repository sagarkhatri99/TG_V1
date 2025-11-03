import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  PersonAdd as AddUserIcon,
  SupervisorAccount as AdminIcon,
  People as UsersIcon,
  AccountCircle as AccountsIcon,
  Work as JobsIcon,
} from '@mui/icons-material';
import api from '../api/Index';
import { useAuth } from '../context/AuthContext';
import { StatsCard } from './StatsCard';
import { PlanDistribution } from './PlanDistribution';
import { UserTable } from './UserTable';
import { UserEditDialog } from './UserEditDialog';

interface User {
  id: number;
  email: string;
  subscription_plan: string;
  created_at: string;
  telegram_accounts_count?: number;
  jobs_count?: number;
  last_login?: string;
}

interface AdminStats {
  total_users: number;
  active_users: number;
  total_accounts: number;
  total_jobs: number;
  plan_distribution: {
    free: number;
    pro: number;
    enterprise: number;
  };
}

export function AdminDashboardContent() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [alert, setAlert] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [editForm, setEditForm] = useState({
    email: '',
    subscription_plan: '',
  });

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/api/admin/users');
      setUsers(response.data.users || []);
    } catch {
      setAlert({ type: 'error', message: 'Failed to fetch users' });
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/admin/stats');
      setStats(response.data);
    } catch (err) {
      console.error('Failed to fetch admin stats', err);
    }
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setEditForm({
      email: user.email,
      subscription_plan: user.subscription_plan,
    });
    setEditDialogOpen(true);
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;

    try {
      await api.put(`/api/admin/users/${selectedUser.id}`, editForm);
      setAlert({ type: 'success', message: 'User updated successfully' });
      setEditDialogOpen(false);
      fetchUsers();
      fetchStats();
    } catch (err) {
      let message = 'Failed to update user';
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data &&
        typeof err.response.data.detail === 'string'
      ) {
        message = err.response.data.detail;
      }
      setAlert({
        type: 'error',
        message,
      });
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user?')) return;

    try {
      await api.delete(`/api/admin/users/${userId}`);
      setAlert({ type: 'success', message: 'User deleted successfully' });
      fetchUsers();
      fetchStats();
    } catch (err) {
      let message = 'Failed to delete user';
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data &&
        typeof err.response.data.detail === 'string'
      ) {
        message = err.response.data.detail;
      }
      setAlert({
        type: 'error',
        message,
      });
    }
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Box>
          <Typography variant="h4">Admin Dashboard</Typography>
          <Typography variant="body1" color="text.secondary">
            Manage users, subscriptions, and system statistics
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddUserIcon />}
          onClick={() => {
            setSelectedUser(null);
            setEditForm({ email: '', subscription_plan: 'free' });
            setEditDialogOpen(true);
          }}
        >
          Add User
        </Button>
      </Box>

      {alert && (
        <Alert
          severity={alert.type}
          onClose={() => setAlert(null)}
          sx={{ mb: 2 }}
        >
          {alert.message}
        </Alert>
      )}

      {stats && (
        <>
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', sm: 'row' },
              flexWrap: 'wrap',
              gap: 3,
              mb: 4,
            }}
          >
            <StatsCard
              title="Total Users"
              value={stats.total_users}
              icon={<UsersIcon color="primary" />}
            />
            <StatsCard
              title="Total Accounts"
              value={stats.total_accounts}
              icon={<AccountsIcon color="secondary" />}
            />
            <StatsCard
              title="Total Jobs"
              value={stats.total_jobs}
              icon={<JobsIcon color="success" />}
            />
            <StatsCard
              title="Active Users"
              value={stats.active_users}
              icon={<AdminIcon color="warning" />}
            />
          </Box>
          <PlanDistribution planDistribution={stats.plan_distribution} />
        </>
      )}

      <UserTable
        users={users}
        currentUser={currentUser}
        onEditUser={handleEditUser}
        onDeleteUser={handleDeleteUser}
      />

      <UserEditDialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        onSave={handleUpdateUser}
        selectedUser={selectedUser}
        editForm={editForm}
        setEditForm={setEditForm}
      />
    </Box>
  );
}
