import React, { useState, useMemo } from 'react';
import { Box, CssBaseline, Drawer, AppBar, Toolbar, List, Typography, Divider, IconButton, ListItem, ListItemButton, ListItemText, Button, ListItemIcon, Chip } from '@mui/material';
import {
  Menu as MenuIcon, 
  Dashboard as DashboardIcon, 
  Logout as LogoutIcon,
  AccountCircle as AccountsIcon,
  Work as JobsIcon,
  PersonSearch as ScrapeIcon,
  Group as MonitorIcon,
  Message as MassDMIcon,
  Speed as DistributedIcon,
  Campaign as AutoPromoIcon,
  Settings as SettingsIcon,
  Help as HelpIcon,
  Dns as ProxiesIcon,
  AdminPanelSettings as AdminIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const drawerWidth = 240;

interface LayoutProps {
  children: React.ReactNode;
}

const allMenuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/', plans: ['free', 'pro', 'enterprise'], isNew: false },
  { text: 'Accounts', icon: <AccountsIcon />, path: '/accounts', plans: ['free', 'pro', 'enterprise'], isNew: false },
  { text: 'Jobs', icon: <JobsIcon />, path: '/jobs', plans: ['free', 'pro', 'enterprise'], isNew: false },
  { text: 'Scrape Users', icon: <ScrapeIcon />, path: '/scrape', plans: ['pro', 'enterprise'], isNew: false },
  { text: 'Monitor Groups', icon: <MonitorIcon />, path: '/monitor', plans: ['pro', 'enterprise'], isNew: false },
  { text: 'Mass DM', icon: <MassDMIcon />, path: '/mass-dm', plans: ['pro', 'enterprise'], isNew: false },
  { text: 'Distributed Mass DM', icon: <DistributedIcon />, path: '/mass-dm-distributed', plans: ['pro', 'enterprise'], isNew: true },
  { text: 'Auto Promo', icon: <AutoPromoIcon />, path: '/auto-promo', plans: ['enterprise'], isNew: true },
  { text: 'Proxies', icon: <ProxiesIcon />, path: '/proxies', plans: ['pro', 'enterprise'], isNew: false },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings', plans: ['free', 'pro', 'enterprise'], isNew: false },
  { text: 'Help', icon: <HelpIcon />, path: '/help', plans: ['free', 'pro', 'enterprise'], isNew: false },
  { text: 'Admin Panel', icon: <AdminIcon />, path: '/admin', plans: ['admin'], isNew: false },
];

export default function Layout({ children }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const menuItems = useMemo(() => {
    if (!user) return [];
    const userPlan = user.subscription_plan || 'free';
    return allMenuItems.filter(item => item.plans.includes(userPlan));
  }, [user]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          TG Tools
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
              sx={{
                borderRadius: 1,
                mx: 1,
                mb: 0.5,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
              {item.isNew && (
                <Chip 
                  label="NEW" 
                  size="small" 
                  color="success" 
                  sx={{ height: 20, fontSize: '0.6rem' }}
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Button variant="contained" startIcon={<LogoutIcon />} onClick={logout} fullWidth>
          Logout
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            TG Tools
          </Typography>
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip 
                label={user.subscription_plan.toUpperCase()} 
                color={user.subscription_plan === 'free' ? 'default' : user.subscription_plan === 'pro' ? 'primary' : 'secondary'}
                size="small"
                variant="outlined"
                sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.3)' }}
              />
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                {user.email}
              </Typography>
            </Box>
          )}
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}