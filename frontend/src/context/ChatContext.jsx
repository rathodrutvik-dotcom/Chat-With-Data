import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { chatAPI } from '../services/api';

const ChatContext = createContext();

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

export const ChatProvider = ({ children }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [sendingMessage, setSendingMessage] = useState(false);

  // Load all sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Load sessions list
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const sessionsData = await chatAPI.getAllSessions();
      setSessions(sessionsData);
      setError(null);
    } catch (err) {
      console.error('Error loading sessions:', err);
      setError('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load a specific session
  const loadSession = useCallback(async (sessionId) => {
    try {
      setLoading(true);
      const [sessionInfo, messagesData] = await Promise.all([
        chatAPI.getSessionInfo(sessionId),
        chatAPI.getSessionMessages(sessionId),
      ]);
      
      setCurrentSession(sessionInfo);
      setMessages(messagesData);
      setError(null);
    } catch (err) {
      console.error('Error loading session:', err);
      setError('Failed to load session');
    } finally {
      setLoading(false);
    }
  }, []);

  // Upload documents
  const uploadDocuments = useCallback(async (files) => {
    try {
      setUploading(true);
      setUploadProgress(0);
      setError(null);

      const result = await chatAPI.uploadDocuments(files, (progress) => {
        setUploadProgress(progress);
      });

      // Reload sessions and select the new one
      await loadSessions();
      await loadSession(result.session_id);
      
      return result;
    } catch (err) {
      console.error('Error uploading documents:', err);
      setError(err.message || 'Failed to upload documents');
      throw err;
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [loadSessions, loadSession]);

  // Send a message
  const sendMessage = useCallback(async (message) => {
    if (!currentSession) {
      setError('No session selected');
      return;
    }

    try {
      setSendingMessage(true);
      setError(null);

      // Add user message optimistically
      const userMessage = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to API
      const response = await chatAPI.sendMessage(currentSession.session_id, message);

      // Add assistant response
      setMessages((prev) => [...prev, response]);
      
      return response;
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message || 'Failed to send message');
      
      // Remove optimistic user message on error
      setMessages((prev) => prev.slice(0, -1));
      throw err;
    } finally {
      setSendingMessage(false);
    }
  }, [currentSession]);

  // Clear current session chat
  const clearChat = useCallback(async () => {
    if (!currentSession) return;

    try {
      await chatAPI.clearSession(currentSession.session_id);
      setMessages([]);
      setError(null);
    } catch (err) {
      console.error('Error clearing chat:', err);
      setError('Failed to clear chat');
    }
  }, [currentSession]);

  // Delete a session
  const deleteSession = useCallback(async (sessionId) => {
    try {
      await chatAPI.deleteSession(sessionId);
      
      // If deleted session is current, clear it
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
      
      // Reload sessions
      await loadSessions();
      setError(null);
    } catch (err) {
      console.error('Error deleting session:', err);
      setError('Failed to delete session');
    }
  }, [currentSession, loadSessions]);

  // Rename a session
  const renameSession = useCallback(async (sessionId, newName) => {
    try {
      const result = await chatAPI.renameSession(sessionId, newName);
      
      // If renamed session is current, update it
      if (currentSession?.session_id === sessionId) {
        setCurrentSession((prev) => ({
          ...prev,
          document_name: result.new_name,
        }));
      }
      
      // Reload sessions to update the list
      await loadSessions();
      setError(null);
      return result;
    } catch (err) {
      console.error('Error renaming session:', err);
      setError('Failed to rename session');
      throw err;
    }
  }, [currentSession, loadSessions]);

  // Create new chat (clear current selection)
  const newChat = useCallback(() => {
    setCurrentSession(null);
    setMessages([]);
    setError(null);
  }, []);

  // Add documents to existing session
  const addDocumentsToSession = useCallback(async (files) => {
    if (!currentSession) {
      setError('No session selected');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      setError(null);

      const result = await chatAPI.addDocumentsToSession(
        currentSession.session_id,
        files,
        (progress) => {
          setUploadProgress(progress);
        }
      );

      // Add system message to messages
      const systemMessage = {
        role: 'system',
        content: result.message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, systemMessage]);

      // Reload session info to get updated document list
      const updatedInfo = await chatAPI.getSessionInfo(currentSession.session_id);
      setCurrentSession(updatedInfo);

      return result;
    } catch (err) {
      console.error('Error adding documents:', err);
      setError(err.message || 'Failed to add documents to session');
      throw err;
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [currentSession]);

  const value = {
    sessions,
    currentSession,
    messages,
    loading,
    uploading,
    uploadProgress,
    error,
    sendingMessage,
    loadSessions,
    loadSession,
    uploadDocuments,
    sendMessage,
    clearChat,
    deleteSession,
    renameSession,
    newChat,
    addDocumentsToSession,
    setError,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export default ChatContext;
