import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Paper,
  Typography,
} from '@mui/material';
import { CheckCircle, Warning, Error } from '@mui/icons-material';
import type { TelegramAccount } from '../Types/Index';

interface RecentAccountsProps {
  accounts: TelegramAccount[];
}

export function RecentAccounts({ accounts }: RecentAccountsProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle color="success" />;
      case 'paused':
        return <Warning color="warning" />;
      case 'error':
        return <Error color="error" />;
      default:
        return <Warning color="action" />;
    }
  };

  const getStatusColor = (
    status: string,
  ): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'paused':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Recent Accounts
      </Typography>
      <List>
        {accounts.slice(0, 5).map((account) => (
          <ListItem key={account.id}>
            <ListItemIcon>{getStatusIcon(account.status)}</ListItemIcon>
            <ListItemText
              primary={account.nickname}
              secondary={account.phone_number}
            />
            <Chip
              label={account.status}
              color={getStatusColor(account.status)}
              size="small"
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
