import axios from 'axios';
import Cookies from 'js-cookie';

const axiosInstance = axios.create({
  baseURL: 'https://api.ogtools.shop',
});

axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token') || Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      Cookies.remove('access_token');
      window.location.href = 'https://ogtools.shop/login';
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;