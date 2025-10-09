import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatComponent } from './components/chat/chat';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent {
  title = 'OEE Co-Pilot';
}