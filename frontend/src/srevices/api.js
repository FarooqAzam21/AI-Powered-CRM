import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 15000,
  withCredentials: true,
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return API(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        // Use a new axios instance to avoid infinite loops on 401 from refresh itself
        const res = await axios.post("http://localhost:8000/auth/refresh", {
          refresh_token: refreshToken
        }, {
          withCredentials: true
        });

        const newAccessToken = res.data.access_token;
        const newRefreshToken = res.data.refresh_token;

        localStorage.setItem("token", newAccessToken);
        if (newRefreshToken) {
          localStorage.setItem("refresh_token", newRefreshToken);
        }

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        
        processQueue(null, newAccessToken);
        return API(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default API;
