import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Box,
  Typography,
  Divider,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { format } from 'date-fns';

interface User {
  id: number;
  email: string;
  subscription_plan: string;
  created_at: string;
  telegram_accounts_count?: number;
  jobs_count?: number;
  last_login?: string;
}

interface UserTableProps {
  users: User[];
  currentUser: User | null;
  onEditUser: (user: User) => void;
  onDeleteUser: (userId: number) => void;
}

export function UserTable({
  users,
  currentUser,
  onEditUser,
  onDeleteUser,
}: UserTableProps) {
  const getPlanColor = (
    plan: string,
  ): 'default' | 'primary' | 'secondary' | 'error' => {
    switch (plan) {
      case 'free':
        return 'default';
      case 'pro':
        return 'primary';
      case 'enterprise':
        return 'secondary';
      case 'admin':
        return 'error';
      default:
        return 'default';
    }
  };
  return (
    <TableContainer component={Paper} elevation={0}>
      <Typography variant="h6" gutterBottom>
        User Management
      </Typography>
      <Divider sx={{ mb: 2 }} />
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
                {u.last_login
                  ? format(new Date(u.last_login), 'MMM dd, HH:mm')
                  : 'Never'}
              </TableCell>
              <TableCell>
                <Box display="flex" gap={1}>
                  <IconButton
                    size="small"
                    onClick={() => onEditUser(u)}
                    color="primary"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => onDeleteUser(u.id)}
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
  );
}
