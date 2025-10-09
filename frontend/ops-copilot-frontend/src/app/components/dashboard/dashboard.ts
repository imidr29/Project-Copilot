import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MetricsCardComponent } from '../metrics-card/metrics-card';
import { ChatComponent } from '../chat/chat';
import { ChatHistoryComponent } from '../chat-history/chat-history';
import { ChatHistoryService, ChatSession } from '../../services/chat-history';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, MetricsCardComponent, ChatComponent, ChatHistoryComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class DashboardComponent implements OnInit {
  currentSession: ChatSession | null = null;

  constructor(private chatHistoryService: ChatHistoryService) {}

  ngOnInit(): void {
    // Initialize with a new session
    this.currentSession = this.chatHistoryService.createNewSession();
  }

  onSessionSelected(session: ChatSession): void {
    this.currentSession = session;
  }

  onNewChatRequested(): void {
    console.log('New chat requested in dashboard');
    this.currentSession = this.chatHistoryService.createNewSession();
    console.log('New session created:', this.currentSession.id);
  }

  onSessionUpdated(session: ChatSession): void {
    this.currentSession = session;
  }
}