import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
} from '@mui/material';
import { CheckCircle } from '@mui/icons-material';

interface SafetyFeaturesProps {
  safetyFeatures: Record<string, string>;
}

export function SafetyFeatures({ safetyFeatures }: SafetyFeaturesProps) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Safety Features
      </Typography>
      <List>
        {Object.entries(safetyFeatures).map(([key, value]) => (
          <ListItem key={key}>
            <ListItemIcon>
              <CheckCircle color={value === 'active' ? 'success' : 'action'} />
            </ListItemIcon>
            <ListItemText
              primary={key
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (l) => l.toUpperCase())}
              secondary={String(value)}
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
