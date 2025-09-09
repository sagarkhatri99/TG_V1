import { createTheme } from '@mui/material/styles';

// Define a modern, dark color palette inspired by sites like Olvy.co
const palette = {
  primary: {
    main: '#6D28D9', // A vibrant purple
    light: '#8B5CF6',
    dark: '#5B21B6',
  },
  secondary: {
    main: '#10B981', // A contrasting green for success states or secondary actions
    light: '#34D399',
    dark: '#059669',
  },
  background: {
    default: '#111827', // Very dark grey, almost black
    paper: '#1F2937',   // Lighter grey for cards and surfaces
  },
  text: {
    primary: '#F9FAFB',   // Off-white for primary text
    secondary: '#9CA3AF', // Lighter grey for secondary text
  },
  divider: '#374151', // For borders
};

const theme = createTheme({
  palette: {
    mode: 'dark',
    ...palette,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontSize: '1.75rem',
      fontWeight: 700,
      color: palette.text.primary,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 600,
      color: palette.text.primary,
    },
    body1: {
      color: palette.text.primary,
    },
    body2: {
      color: palette.text.secondary,
    },
  },
  shape: {
    borderRadius: 12, // Slightly more rounded corners for a modern feel
  },
  components: {
    // General overrides
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none', // Remove gradients from paper components
        },
      },
    },
    // Button overrides
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
          boxShadow: 'none',
        },
        containedPrimary: {
          '&:hover': {
            backgroundColor: palette.primary.light,
            boxShadow: `0 0 20px 0 ${palette.primary.dark}`,
          },
        },
      },
    },
    // Card overrides
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${palette.divider}`,
          borderRadius: 16,
          boxShadow: 'none',
          transition: 'border-color 0.3s, box-shadow 0.3s',
          '&:hover': {
            borderColor: palette.primary.dark,
            boxShadow: `0 0 15px 0 ${palette.primary.dark}`,
          },
        },
      },
    },
    // TextField overrides
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: palette.divider,
            },
            '&:hover fieldset': {
              borderColor: palette.primary.light,
            },
            '&.Mui-focused fieldset': {
              borderColor: palette.primary.main,
            },
          },
        },
      },
    },
    // Chip overrides
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    // Table overrides
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${palette.divider}`,
        },
        head: {
          fontWeight: 600,
          color: palette.text.secondary,
        }
      }
    }
  },
});

export default theme;
