import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button, CircularProgress, Alert } from '@mui/material';

const JobList: React.FC = () => {
  const { data, error, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => axios.get('/api/jobs/list').then(res => {
      console.log(res.data.jobs);
      return res.data.jobs;
    }),
    refetchInterval: 10000,
  });

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">Error fetching jobs</Alert>;

  const handleDownload = (jobId: number) => {
    window.open(`/api/jobs/${jobId}/result`, '_blank');
  };

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Job ID</TableCell>
            <TableCell>Job Type</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Created At</TableCell>
            <TableCell>Error</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.map((job: any) => (
            <TableRow key={job.id}>
              <TableCell>{job.id}</TableCell>
              <TableCell>{job.job_type}</TableCell>
              <TableCell>{job.status}</TableCell>
              <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
              <TableCell>{job.error_message}</TableCell>
              <TableCell>
                {job.status === 'completed' && job.result_path && (
                  <Button onClick={() => handleDownload(job.id)}>Download Result</Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default JobList;