import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  PersonAdd as AddUserIcon,
  SupervisorAccount as AdminIcon,
  People as UsersIcon,
  AccountCircle as AccountsIcon,
  Work as JobsIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import api from '../api/Index';
import { useAuth } from '../context/AuthContext';

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

export default function AdminDashboard() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [alert, setAlert] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [editForm, setEditForm] = useState({
    email: '',
    subscription_plan: '',
  });

// Only allow admin users
  if (currentUser?.subscription_plan !== 'admin') {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Alert severity="error">
          Access denied. Admin privileges required.
        </Alert>
      </Box>
    );
  }

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/api/admin/users');
      setUsers(response.data.users || []);
    } catch (error) {
      setAlert({ type: 'error', message: 'Failed to fetch users' });
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/admin/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch admin stats', error);
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
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to update user' });
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user?')) return;

    try {
      await api.delete(`/api/admin/users/${userId}`);
      setAlert({ type: 'success', message: 'User deleted successfully' });
      fetchUsers();
      fetchStats();
    } catch (error: any) {
      setAlert({ type: 'error', message: error.response?.data?.detail || 'Failed to delete user' });
    }
  };

  const getPlanColor = (plan: string): any => {
    switch (plan) {
      case 'free': return 'default';
      case 'pro': return 'primary';
      case 'enterprise': return 'secondary';
      case 'admin': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
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

      {/* Statistics Cards */}
      {stats && (
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, flexWrap: 'wrap', gap: 3, mb: 4 }}>
          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Total Users
                    </Typography>
                    <Typography variant="h4">
                      {stats.total_users}
                    </Typography>
                  </Box>
                  <UsersIcon color="primary" />
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Total Accounts
                    </Typography>
                    <Typography variant="h4">
                      {stats.total_accounts}
                    </Typography>
                  </Box>
                  <AccountsIcon color="secondary" />
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Total Jobs
                    </Typography>
                    <Typography variant="h4">
                      {stats.total_jobs}
                    </Typography>
                  </Box>
                  <JobsIcon color="success" />
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="body2">
                      Active Users
                    </Typography>
                    <Typography variant="h4">
                      {stats.active_users}
                    </Typography>
                  </Box>
                  <AdminIcon color="warning" />
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Box>
      )}

      {/* Plan Distribution */}
      {stats && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Subscription Plan Distribution
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'space-around' }}>
              <Box textAlign="center">
                <Typography variant="h5" color="text.secondary">
                  {stats.plan_distribution.free}
                </Typography>
                <Typography variant="body2">Free</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="h5" color="primary">
                  {stats.plan_distribution.pro}
                </Typography>
                <Typography variant="body2">Pro</Typography>
              </Box>
              <Box textAlign="center">
                <Typography variant="h5" color="secondary">
                  {stats.plan_distribution.enterprise}
                </Typography>
                <Typography variant="body2">Enterprise</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            User Management
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell>Plan</TableCell>
                  <TableCell>Accounts</TableCell>
                  <TableCell>Jobs</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Last Login</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
{users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>
                      <Box>
<Typography variant="subtitle2">{u.email}</Typography>
                        <Typography variant="caption" color="text.secondary">
ID: {u.id}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip 
label={u.subscription_plan.toUpperCase()}
color={getPlanColor(u.subscription_plan)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
<TableCell>{u.telegram_accounts_count || 0}</TableCell>
<TableCell>{u.jobs_count || 0}</TableCell>
                    <TableCell>
{format(new Date(u.created_at), 'MMM dd, yyyy')}
                    </TableCell>
                    <TableCell>
{u.last_login ? 
                        format(new Date(u.last_login), 'MMM dd, HH:mm') : 
                        'Never'
                      }
                    </TableCell>
                    <TableCell>
                      <Box display="flex" gap={1}>
                        <IconButton 
                          size="small" 
onClick={() => handleEditUser(u)}
                          color="primary"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton 
                          size="small" 
onClick={() => handleDeleteUser(u.id)}
                          color="error"
disabled={currentUser ? u.id === currentUser.id : false} // Prevent self-deletion
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Edit/Add User Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedUser ? 'Edit User' : 'Add New User'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={editForm.email}
              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
            />
            <FormControl fullWidth>
              <InputLabel>Subscription Plan</InputLabel>
              <Select
                value={editForm.subscription_plan}
                label="Subscription Plan"
                onChange={(e) => setEditForm({ ...editForm, subscription_plan: e.target.value })}
              >
                <MenuItem value="free">Free</MenuItem>
                <MenuItem value="pro">Pro</MenuItem>
                <MenuItem value="enterprise">Enterprise</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateUser} variant="contained">
            {selectedUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}