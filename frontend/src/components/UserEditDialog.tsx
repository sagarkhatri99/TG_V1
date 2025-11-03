import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
} from '@mui/material';

interface User {
  id: number;
  email: string;
  subscription_plan: string;
}

interface EditForm {
  email: string;
  subscription_plan: string;
}

interface UserEditDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: () => void;
  selectedUser: User | null;
  editForm: EditForm;
  setEditForm: (form: EditForm) => void;
}

export function UserEditDialog({
  open,
  onClose,
  onSave,
  selectedUser,
  editForm,
  setEditForm,
}: UserEditDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{selectedUser ? 'Edit User' : 'Add New User'}</DialogTitle>
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
              onChange={(e) =>
                setEditForm({ ...editForm, subscription_plan: e.target.value })
              }
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
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onSave} variant="contained">
          {selectedUser ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
