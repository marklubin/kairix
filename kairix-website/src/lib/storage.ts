import type { Message } from 'ai';

interface ChatSession {
  endpoint: string;
  model: string;
  messages: Message[];
  lastUpdated: number;
}

const STORAGE_KEY = 'kairix-chat-sessions';
const MAX_CONTEXT_MESSAGES = 20;

// Set default API key if not present
if (!localStorage.getItem('apiKey')) {
  localStorage.setItem('apiKey', 'test-api-key-12345');
}

export class ChatStorage {
  static getAllSessions(): Record<string, ChatSession> {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.error('Error loading chat sessions:', error);
      return {};
    }
  }

  static getSession(endpoint: string, model: string): Message[] {
    const sessions = this.getAllSessions();
    const key = `${endpoint}:${model}`;
    return sessions[key]?.messages || [];
  }

  static saveSession(endpoint: string, model: string, messages: Message[]): void {
    try {
      const sessions = this.getAllSessions();
      const key = `${endpoint}:${model}`;
      
      sessions[key] = {
        endpoint,
        model,
        messages,
        lastUpdated: Date.now()
      };

      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.error('Error saving chat session:', error);
    }
  }

  static getContextMessages(messages: Message[]): Message[] {
    // Return only the last MAX_CONTEXT_MESSAGES for API context
    if (messages.length <= MAX_CONTEXT_MESSAGES) {
      return messages;
    }
    
    return messages.slice(-MAX_CONTEXT_MESSAGES);
  }

  static clearSession(endpoint: string, model: string): void {
    try {
      const sessions = this.getAllSessions();
      const key = `${endpoint}:${model}`;
      delete sessions[key];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.error('Error clearing chat session:', error);
    }
  }

  static clearAllSessions(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Error clearing all sessions:', error);
    }
  }
}