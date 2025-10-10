import { Component, OnInit, OnChanges, ViewChild, ElementRef, AfterViewChecked, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NgxEchartsDirective } from 'ngx-echarts';
import { ApiService, QueryRequest, QueryResponse } from '../../services/api';
import { ChatHistoryService, ChatSession, ChatMessage } from '../../services/chat-history';

// Remove duplicate interface - using the one from chat-history service

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxEchartsDirective],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class ChatComponent implements OnInit, OnChanges, AfterViewChecked {
  @ViewChild('chatMessages') chatMessages!: ElementRef;
  @Input() currentSession: ChatSession | null = null;
  @Input() apiToken: string | null = null;
  @Output() sessionUpdated = new EventEmitter<ChatSession>();

  messages: ChatMessage[] = [];
  currentMessage: string = '';
  isLoading: boolean = false;
  isTyping: boolean = false;
  isUserScrolling: boolean = false;
  conversationHistory: Array<{role: string, content: string}> = [];
  
  // Enhanced loading states for slow LLM/Pinecone operations
  loadingStage: string = '';
  loadingProgress: number = 0;
  estimatedTimeRemaining: number = 0;
  queryStartTime: number = 0;
  
  // Query suggestions
  suggestions: string[] = [];
  showSuggestions: boolean = true;

  chartInitOpts = {
    renderer: 'canvas',
    width: 'auto',
    height: 300
  };

  // Chart options for different chart types
  getChartOptions(chartSpec: any): any {
    if (!chartSpec) {
      console.log('No chart spec provided');
      return null;
    }
    
    try {
      console.log('Processing chart spec:', chartSpec);
      
      // Ensure proper chart configuration with enhanced styling
      const options = {
        ...chartSpec,
        animation: true,
        animationDuration: 1000,
        animationEasing: 'cubicOut',
        // Ensure responsive design
        responsive: true,
        maintainAspectRatio: false,
        // Enhanced styling
        backgroundColor: 'transparent',
        textStyle: {
          fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontSize: 12,
          color: '#4a5568'
        },
        // Enhanced tooltip
        tooltip: {
          ...chartSpec.tooltip,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          textStyle: {
            color: '#2d3748',
            fontSize: 12
          },
          extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); border-radius: 8px;'
        },
        // Enhanced legend
        legend: {
          ...chartSpec.legend,
          textStyle: {
            color: '#4a5568',
            fontSize: 12
          }
        },
        // Enhanced title
        title: {
          ...chartSpec.title,
          textStyle: {
            color: '#2d3748',
            fontSize: 16,
            fontWeight: '600'
          }
        },
        // Enhanced grid
        grid: {
          ...chartSpec.grid,
          backgroundColor: 'transparent',
          borderColor: '#e2e8f0',
          borderWidth: 1
        },
        // Enhanced xAxis
        xAxis: {
          ...chartSpec.xAxis,
          axisLine: {
            lineStyle: {
              color: '#e2e8f0'
            }
          },
          axisTick: {
            lineStyle: {
              color: '#e2e8f0'
            }
          },
          axisLabel: {
            color: '#718096',
            fontSize: 11
          }
        },
        // Enhanced yAxis
        yAxis: {
          ...chartSpec.yAxis,
          axisLine: {
            lineStyle: {
              color: '#e2e8f0'
            }
          },
          axisTick: {
            lineStyle: {
              color: '#e2e8f0'
            }
          },
          axisLabel: {
            color: '#718096',
            fontSize: 11
          }
        },
        // Enhanced series styling
        series: chartSpec.series?.map((s: any) => ({
          ...s,
          itemStyle: {
            ...s.itemStyle,
            borderRadius: s.type === 'bar' ? [4, 4, 0, 0] : undefined
          },
          lineStyle: s.lineStyle ? {
            ...s.lineStyle,
            width: 3
          } : undefined,
          areaStyle: s.areaStyle ? {
            ...s.areaStyle,
            opacity: 0.1
          } : undefined
        }))
      };
      
      console.log('Final chart options:', options);
      return options;
    } catch (error) {
      console.error('Error processing chart options:', error);
      return null;
    }
  }

  constructor(
    private apiService: ApiService,
    private chatHistoryService: ChatHistoryService
  ) {}

  ngOnInit() {
    if (this.currentSession) {
      this.loadSession(this.currentSession);
    } else {
      this.initializeNewSession();
    }
    this.loadSuggestions();
  }

  ngOnChanges() {
    if (this.currentSession) {
      this.loadSession(this.currentSession);
    }
  }

  private loadSession(session: ChatSession): void {
    this.messages = [...session.messages];
    this.conversationHistory = [...session.conversationHistory];
  }

  private initializeNewSession(): void {
    this.messages = [{
      content: "Hello! I'm your Operations Co-Pilot. I can help you analyze equipment deployment, production metrics, quality data, fuel consumption, and maintenance schedules across all your mining operations. What would you like to know?",
      timestamp: new Date(),
      isUser: false
    }];
    this.conversationHistory = [];
  }

  ngAfterViewChecked() {
    // Use setTimeout to prevent blocking the UI
    setTimeout(() => {
      if (!this.isUserScrolling) {
        this.scrollToBottom();
      }
    }, 0);
  }

  onEnterKey(event: Event) {
    const keyboardEvent = event as KeyboardEvent;
    if (keyboardEvent.key === 'Enter' && !keyboardEvent.shiftKey) {
      keyboardEvent.preventDefault();
      this.sendMessage();
    }
  }

      async sendMessage() {
        if (!this.currentMessage.trim() || this.isLoading) return;

        const userMessage = this.currentMessage.trim();
        
        // Add user message to the unified messages array
        this.messages.push({
          content: userMessage,
          timestamp: new Date(),
          isUser: true
        });

        this.currentMessage = '';
        this.isLoading = true;
        this.isTyping = true;
        this.queryStartTime = Date.now();
        this.startLoadingProgress();

        // Add to conversation history
        this.conversationHistory.push({ role: 'user', content: userMessage });

        // Use setTimeout to allow UI to update before processing
        setTimeout(async () => {
          try {
            const request: QueryRequest = {
              query: userMessage,
              conversation_history: this.conversationHistory.slice(-6) // Keep only last 6 messages (3 exchanges)
            };

            this.updateLoadingStage('Processing with Gemini 2.0 Flash...', 20);
            
            const response: QueryResponse = await this.apiService.processQuery(request, this.apiToken || undefined).toPromise() as QueryResponse;

            this.updateLoadingStage('Generating visualization...', 80);

            // Add bot response to conversation history
            this.conversationHistory.push({ role: 'assistant', content: response.natural_language_response });

            // Add bot message with results and SQL query
            this.messages.push({
              content: response.natural_language_response,
              timestamp: new Date(),
              chartSpec: response.chart_spec,
              results: response.results,
              sqlQuery: response.sql_query,
              metadata: response.metadata,
              isUser: false,
              currentPage: 1
            });

            this.updateLoadingStage('Complete!', 100);

            // Save session after each exchange
            this.saveCurrentSession();

          } catch (error) {
            console.error('Error sending message:', error);
            this.messages.push({
              content: this.getErrorMessage(error),
              timestamp: new Date(),
              isUser: false
            });
          } finally {
            this.isLoading = false;
            this.isTyping = false;
            this.resetLoadingState();
          }
        }, 100); // Small delay to allow UI to update
      }

  getTableHeaders(results: any[]): string[] {
    if (!results || results.length === 0) return [];
    return Object.keys(results[0]);
  }

  getCurrentPage(message: ChatMessage): number {
    return message.currentPage || 1;
  }

  getTotalPages(message: ChatMessage): number {
    if (!message.results) return 1;
    return Math.ceil(message.results.length / 50);
  }

  getCurrentPageStart(message: ChatMessage): number {
    const page = this.getCurrentPage(message);
    return (page - 1) * 50 + 1;
  }

  getCurrentPageEnd(message: ChatMessage): number {
    const page = this.getCurrentPage(message);
    const start = this.getCurrentPageStart(message);
    return Math.min(start + 49, message.results?.length || 0);
  }

  getCurrentPageData(message: ChatMessage): any[] {
    if (!message.results) return [];
    const page = this.getCurrentPage(message);
    const start = (page - 1) * 50;
    const end = start + 50;
    return message.results.slice(start, end);
  }

  previousPage(message: ChatMessage): void {
    if (message.currentPage && message.currentPage > 1) {
      message.currentPage--;
    }
  }

  nextPage(message: ChatMessage): void {
    const totalPages = this.getTotalPages(message);
    if (!message.currentPage || message.currentPage < totalPages) {
      message.currentPage = (message.currentPage || 1) + 1;
    }
  }

  clearConversation(): void {
    this.conversationHistory = [];
    this.messages = [{
      content: "Hello! I'm your Operations Co-Pilot. I can help you analyze equipment deployment, production metrics, quality data, fuel consumption, and maintenance schedules across all your mining operations. What would you like to know?",
      timestamp: new Date(),
      isUser: false
    }];
    this.saveCurrentSession();
  }

  createNewChat(): void {
    const newSession = this.chatHistoryService.createNewSession();
    this.currentSession = newSession;
    this.loadSession(newSession);
    this.sessionUpdated.emit(newSession);
  }

  private saveCurrentSession(): void {
    if (this.currentSession) {
      // Update existing session
      this.currentSession.messages = [...this.messages];
      this.currentSession.conversationHistory = [...this.conversationHistory];
      this.currentSession.lastModified = new Date();
      
      // Generate title from first user message if still "New Chat"
      if (this.currentSession.title === 'New Chat') {
        this.currentSession.title = this.chatHistoryService.generateTitleFromFirstMessage(this.messages);
      }
      
      this.chatHistoryService.saveSession(this.currentSession);
      this.sessionUpdated.emit(this.currentSession);
    } else {
      // Create new session
      const newSession = this.chatHistoryService.createNewSession();
      newSession.messages = [...this.messages];
      newSession.conversationHistory = [...this.conversationHistory];
      newSession.title = this.chatHistoryService.generateTitleFromFirstMessage(this.messages);
      
      this.chatHistoryService.saveSession(newSession);
      this.currentSession = newSession;
      this.sessionUpdated.emit(newSession);
    }
  }


  onScroll(event: Event) {
    const element = event.target as HTMLElement;
    const threshold = 50; // pixels from bottom
    
    // Check if user is near the bottom
    if (element.scrollTop + element.clientHeight >= element.scrollHeight - threshold) {
      this.isUserScrolling = false;
    } else {
      this.isUserScrolling = true;
    }
  }

  private scrollToBottom() {
    try {
      if (this.chatMessages) {
        const element = this.chatMessages.nativeElement;
        // Use requestAnimationFrame for smooth scrolling
        requestAnimationFrame(() => {
          element.scrollTop = element.scrollHeight;
        });
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  // Utility methods for formatting
  formatMessage(content: string): string {
    return content.replace(/\n/g, '<br>');
  }

  formatTimestamp(timestamp: Date): string {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  formatHeader(header: string): string {
    return header.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatCellValue(value: any): string {
    if (value === null || value === undefined) {
      return '-';
    }
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    if (typeof value === 'string' && value.length > 50) {
      return value.substring(0, 50) + '...';
    }
    return String(value);
  }

  async copyToClipboard(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here
      console.log('Copied to clipboard');
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  }

  trackByMessage(index: number, message: ChatMessage): any {
    return message.timestamp.getTime() + (message.isUser ? 'user' : 'bot');
  }

  // Helper method for JSON stringification in templates
  stringifyResults(results: any[]): string {
    return JSON.stringify(results, null, 2);
  }

  // Enhanced loading state management for slow LLM/Pinecone operations
  private startLoadingProgress(): void {
    this.loadingStage = 'Initializing query...';
    this.loadingProgress = 0;
    this.estimatedTimeRemaining = 30; // Initial estimate in seconds
    
    // Simulate progress updates
    const progressInterval = setInterval(() => {
      if (!this.isLoading) {
        clearInterval(progressInterval);
        return;
      }
      
      const elapsed = (Date.now() - this.queryStartTime) / 1000;
      this.estimatedTimeRemaining = Math.max(0, 30 - elapsed);
      
      // Gradually increase progress if no specific stage update
      if (this.loadingProgress < 15) {
        this.loadingProgress += 0.5;
      }
    }, 500);
  }

  private updateLoadingStage(stage: string, progress: number): void {
    this.loadingStage = stage;
    this.loadingProgress = progress;
  }

  private resetLoadingState(): void {
    this.loadingStage = '';
    this.loadingProgress = 0;
    this.estimatedTimeRemaining = 0;
  }

  private getErrorMessage(error: any): string {
    if (error.message?.includes('timeout')) {
      return "The query is taking longer than expected. This might be due to complex data processing or Pinecone vector search. Please try a simpler query or wait a bit longer.";
    } else if (error.message?.includes('network')) {
      return "Network connection issue. Please check your internet connection and try again.";
    } else if (error.message?.includes('500')) {
      return "Server error occurred. The LLM or Pinecone service might be experiencing issues. Please try again in a moment.";
    } else {
      return "I encountered an error processing your request. This might be due to the complexity of your query or temporary service issues. Please try rephrasing your question or try again later.";
    }
  }

  // Format time remaining for display
  formatTimeRemaining(seconds: number): string {
    if (seconds <= 0) return 'Almost done...';
    if (seconds < 60) return `${Math.round(seconds)}s remaining`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s remaining`;
  }

  // Load query suggestions
  private loadSuggestions(): void {
    this.apiService.getQuerySuggestions().subscribe({
      next: (suggestions) => {
        this.suggestions = suggestions;
      },
      error: (error) => {
        console.error('Failed to load suggestions:', error);
        // Fallback suggestions
        this.suggestions = [
          "What % of time was the machine ACTIVE vs INACTIVE today?",
          "Show me all INACTIVE episodes less than 60 seconds",
          "Top 5 reasons contributing to INACTIVE time",
          "Trend of daily total INACTIVE minutes over last 14 days",
          "Calculate approximate MTTR for last week"
        ];
      }
    });
  }

  // Use suggestion
  useSuggestion(suggestion: string): void {
    this.currentMessage = suggestion;
    this.showSuggestions = false;
    this.sendMessage();
  }

  // Toggle suggestions visibility
  toggleSuggestions(): void {
    this.showSuggestions = !this.showSuggestions;
  }
}