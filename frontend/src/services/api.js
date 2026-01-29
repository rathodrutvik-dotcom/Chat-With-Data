import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || 'An error occurred';
    console.error('API Error:', message);
    return Promise.reject(new Error(message));
  }
);

// API Services
export const chatAPI = {
  // Session Management
  getAllSessions: async () => {
    const response = await api.get('/sessions');
    return response.data;
  },

  getSessionMessages: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}/messages`);
    return response.data;
  },

  getSessionInfo: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}/info`);
    return response.data;
  },

  clearSession: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/clear`);
    return response.data;
  },

  renameSession: async (sessionId, newName) => {
    const response = await api.patch(`/sessions/${sessionId}/rename?new_name=${encodeURIComponent(newName)}`);
    return response.data;
  },


  deleteSession: async (sessionId) => {
    const response = await api.delete(`/sessions/${sessionId}`);
    return response.data;
  },

  searchChats: async (query) => {
    const response = await api.get(`/search?q=${encodeURIComponent(query)}`);
    return response.data;
  },

  // Document Upload
  uploadDocuments: async (files, onProgress) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
    return response.data;
  },

  // Add documents to existing session
  addDocumentsToSession: async (sessionId, files, onProgress) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post(`/sessions/${sessionId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
    return response.data;
  },

  // URL Upload
  uploadURLs: async (urls, onProgress) => {
    // Simulate progress for URL upload since it's not multipart
    if (onProgress) {
      onProgress(10); // Start at 10%
    }

    const response = await api.post('/upload-urls', {
      urls: urls,
    });

    if (onProgress) {
      onProgress(100); // Complete
    }

    return response.data;
  },

  // Add URLs to existing session
  addURLsToSession: async (sessionId, urls, onProgress) => {
    if (onProgress) {
      onProgress(10);
    }

    const response = await api.post(`/sessions/${sessionId}/urls`, {
      urls: urls,
    });

    if (onProgress) {
      onProgress(100);
    }

    return response.data;
  },

  // Chat
  sendMessage: async (sessionId, message) => {
    const response = await api.post('/chat', {
      session_id: sessionId,
      message: message,
    });
    return response.data;
  },

  // Health Check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
