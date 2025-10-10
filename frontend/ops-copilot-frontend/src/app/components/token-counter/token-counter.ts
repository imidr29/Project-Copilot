import { Component, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api';

interface UsageStats {
  user_id: string;
  role: string;
  total_requests: number;
  daily_requests: number;
  total_tokens: number;
  last_reset: string;
  tokens: Array<{
    token: string;
    role: string;
    created_at: string;
    expires_at: string;
    requests: number;
  }>;
}

interface SystemStats {
  total_users: number;
  total_requests: number;
  total_tokens: number;
  active_tokens: number;
  daily_requests: number;
  rate_limit_per_hour: number;
  token_expiry_hours: number;
}

@Component({
  selector: 'app-token-counter',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './token-counter.html',
  styleUrls: ['./token-counter.scss']
})
export class TokenCounterComponent implements OnInit {
  @Input() showSystemStats: boolean = false;
  @Input() apiToken: string | null = null;

  usageStats: UsageStats | null = null;
  systemStats: SystemStats | null = null;
  loading = false;
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    console.log('TokenCounter initialized with token:', this.apiToken ? this.apiToken.substring(0, 8) + '...' : 'None');
    console.log('Show system stats:', this.showSystemStats);
    
    if (this.apiToken) {
      this.loadUsageStats();
      if (this.showSystemStats) {
        this.loadSystemStats();
      }
    } else {
      console.log('No token provided to TokenCounter component');
    }
  }

  loadUsageStats() {
    if (!this.apiToken) {
      this.error = 'No API token provided';
      return;
    }

    this.loading = true;
    this.error = null;

    this.apiService.getUsageStats(this.apiToken).subscribe({
      next: (stats) => {
        this.usageStats = stats;
        this.loading = false;
      },
      error: (error) => {
        this.error = 'Failed to load usage statistics';
        this.loading = false;
        console.error('Error loading usage stats:', error);
      }
    });
  }

  loadSystemStats() {
    if (!this.apiToken) {
      return;
    }

    this.apiService.getSystemStats(this.apiToken).subscribe({
      next: (stats) => {
        this.systemStats = stats;
      },
      error: (error) => {
        console.error('Error loading system stats:', error);
      }
    });
  }

  refreshStats() {
    this.loadUsageStats();
    if (this.showSystemStats) {
      this.loadSystemStats();
    }
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString();
  }

  formatDateTime(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  getRemainingRequests(): number {
    if (!this.usageStats) return 0;
    return Math.max(0, 100 - this.usageStats.daily_requests);
  }

  getUsagePercentage(): number {
    if (!this.usageStats) return 0;
    return Math.min(100, (this.usageStats.daily_requests / 100) * 100);
  }

  getUsageColor(): string {
    const percentage = this.getUsagePercentage();
    if (percentage >= 90) return 'danger';
    if (percentage >= 70) return 'warning';
    return 'success';
  }
}
