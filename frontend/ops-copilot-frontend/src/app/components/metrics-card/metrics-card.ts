import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-metrics-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './metrics-card.html',
  styleUrl: './metrics-card.scss'
})
export class MetricsCardComponent {
  @Input() title: string = '';
  @Input() value: string = '';
  @Input() unit: string = '';
  @Input() changeText: string = '';
  @Input() changeType: 'positive' | 'negative' | 'neutral' = 'neutral';

  get changeClass(): string {
    return this.changeType;
  }

  get changeIcon(): string {
    switch (this.changeType) {
      case 'positive':
        return '↗';
      case 'negative':
        return '↘';
      case 'neutral':
        return '→';
      default:
        return '→';
    }
  }
}