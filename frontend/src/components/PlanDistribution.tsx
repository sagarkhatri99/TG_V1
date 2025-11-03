import { Card, CardContent, Typography, Box } from '@mui/material';

interface PlanDistributionProps {
  planDistribution: {
    free: number;
    pro: number;
    enterprise: number;
  };
}

export function PlanDistribution({
  planDistribution,
}: PlanDistributionProps) {
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Subscription Plan Distribution
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'space-around' }}>
          <Box textAlign="center">
            <Typography variant="h5" color="text.secondary">
              {planDistribution.free}
            </Typography>
            <Typography variant="body2">Free</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h5" color="primary">
              {planDistribution.pro}
            </Typography>
            <Typography variant="body2">Pro</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h5" color="secondary">
              {planDistribution.enterprise}
            </Typography>
            <Typography variant="body2">Enterprise</Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
