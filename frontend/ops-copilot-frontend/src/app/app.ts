import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatComponent } from './components/chat/chat';
import { TokenCounterComponent } from './components/token-counter/token-counter';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatComponent, TokenCounterComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent implements OnInit {
  title = 'OEE Co-Pilot';
  apiToken: string | null = null;
  isAdmin: boolean = false;

  ngOnInit() {
    // Try to get token from localStorage or prompt user
    this.loadTokenFromStorage();
    console.log('App initialized - Token status:', this.apiToken ? 'Set' : 'Not Set');
  }

  loadTokenFromStorage() {
    const storedToken = localStorage.getItem('api_token');
    if (storedToken) {
      this.apiToken = storedToken;
      // Check if user is admin (you can enhance this logic)
      this.isAdmin = this.checkIfAdmin(storedToken);
    }
  }

  setToken(token: string) {
    console.log('Setting token:', token.substring(0, 8) + '...');
    this.apiToken = token;
    localStorage.setItem('api_token', token);
    this.isAdmin = this.checkIfAdmin(token);
    console.log('Token set - Admin status:', this.isAdmin);
  }

  clearToken() {
    this.apiToken = null;
    localStorage.removeItem('api_token');
    this.isAdmin = false;
  }

  private checkIfAdmin(token: string): boolean {
    // Simple check - you can enhance this by making an API call
    // For now, we'll assume admin tokens are longer or have specific patterns
    return token.length > 30; // This is just a placeholder logic
  }
}