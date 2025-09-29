import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#7c3aed',
      light: '#a855f7',
      dark: '#6b21a8',
    },
    secondary: {
      main: '#06d6a0',
      light: '#34d399',
      dark: '#059669',
    },
    background: {
      default: '#0f1419',
      paper: '#1a202c',
    },
    text: {
      primary: '#f7fafc',
      secondary: '#a0aec0',
    },
    error: {
      main: '#f56565',
    },
    warning: {
      main: '#ed8936',
    },
    success: {
      main: '#48bb78',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: 8,
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.15)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.3)',
          backgroundColor: '#2d3748',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(124, 58, 237, 0.15)',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1a202c',
          borderRight: '1px solid #2d3748',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a202c',
          borderBottom: '1px solid #2d3748',
        },
      },
    },
  },
});

export default theme;
