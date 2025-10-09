import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatHistoryService, ChatSession } from '../../services/chat-history';

@Component({
  selector: 'app-chat-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './chat-history.html',
  styleUrl: './chat-history.scss'
})
export class ChatHistoryComponent implements OnInit {
  @Input() currentSessionId: string | null = null;
  @Output() sessionSelected = new EventEmitter<ChatSession>();
  @Output() newChatRequested = new EventEmitter<void>();

  sessions: ChatSession[] = [];

  constructor(private chatHistoryService: ChatHistoryService) {}

  ngOnInit() {
    this.loadSessions();
  }

  loadSessions(): void {
    this.sessions = this.chatHistoryService.getAllSessions();
  }

  selectSession(session: ChatSession): void {
    this.sessionSelected.emit(session);
  }

  createNewChat(): void {
    console.log('New chat button clicked');
    this.newChatRequested.emit();
  }

  deleteSession(sessionId: string, event: Event): void {
    event.stopPropagation(); // Prevent session selection
    if (confirm('Are you sure you want to delete this chat?')) {
      this.chatHistoryService.deleteSession(sessionId);
      this.loadSessions();
      
      // If we deleted the current session, emit new chat request
      if (this.currentSessionId === sessionId) {
        this.newChatRequested.emit();
      }
    }
  }
}