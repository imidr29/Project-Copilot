import { Injectable } from '@angular/core';

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  lastModified: Date;
  messages: ChatMessage[];
  conversationHistory: Array<{role: string, content: string}>;
}

export interface ChatMessage {
  content: string;
  timestamp: Date;
  chartSpec?: any;
  results?: any[];
  sqlQuery?: string;
  metadata?: {
    result_count: number;
    execution_time_ms: number;
    chart_type?: string;
  };
  isUser: boolean;
  currentPage?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ChatHistoryService {
  private readonly STORAGE_KEY = 'ops_copilot_chat_history';
  private readonly MAX_SESSIONS = 50;

  constructor() { }

  saveSession(session: ChatSession): void {
    const sessions = this.getAllSessions();
    
    // Update existing session or add new one
    const existingIndex = sessions.findIndex(s => s.id === session.id);
    if (existingIndex >= 0) {
      sessions[existingIndex] = session;
    } else {
      sessions.unshift(session);
    }
    
    // Limit number of saved sessions
    if (sessions.length > this.MAX_SESSIONS) {
      sessions.splice(this.MAX_SESSIONS);
    }
    
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(sessions));
  }

  getAllSessions(): ChatSession[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (!stored) return [];
      
      const sessions = JSON.parse(stored);
      return sessions.map((session: any) => ({
        ...session,
        createdAt: new Date(session.createdAt),
        lastModified: new Date(session.lastModified),
        messages: session.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
      }));
    } catch (error) {
      console.error('Error loading chat history:', error);
      return [];
    }
  }

  getSession(id: string): ChatSession | null {
    const sessions = this.getAllSessions();
    return sessions.find(s => s.id === id) || null;
  }

  deleteSession(id: string): void {
    const sessions = this.getAllSessions();
    const filtered = sessions.filter(s => s.id !== id);
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filtered));
  }

  createNewSession(): ChatSession {
    const id = this.generateId();
    const now = new Date();
    
    return {
      id,
      title: 'New Chat',
      createdAt: now,
      lastModified: now,
      messages: [{
        content: "Hello! I'm your Operations Co-Pilot. I can help you analyze equipment deployment, production metrics, quality data, fuel consumption, and maintenance schedules across all your mining operations. What would you like to know?",
        timestamp: now,
        isUser: false
      }],
      conversationHistory: []
    };
  }

  updateSessionTitle(id: string, title: string): void {
    const session = this.getSession(id);
    if (session) {
      session.title = title;
      session.lastModified = new Date();
      this.saveSession(session);
    }
  }

  generateTitleFromFirstMessage(messages: ChatMessage[]): string {
    const firstUserMessage = messages.find(msg => msg.isUser);
    if (firstUserMessage) {
      const content = firstUserMessage.content;
      // Truncate long messages and clean up
      return content.length > 50 ? content.substring(0, 47) + '...' : content;
    }
    return 'New Chat';
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }
}