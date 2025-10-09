import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Region {
  name: string;
  status: string;
}

interface DataSource {
  name: string;
  type: string;
  latency: string;
}

@Component({
  selector: 'app-status-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './status-sidebar.html',
  styleUrl: './status-sidebar.scss'
})
export class StatusSidebarComponent {
  regions: Region[] = [
    { name: 'India', status: 'Connected' },
    { name: 'Australia', status: 'Connected' },
    { name: 'UAE', status: 'Connected' },
    { name: 'Africa', status: 'Connected' },
    { name: 'Europe', status: 'Connected' }
  ];

  dataSources: DataSource[] = [
    { name: 'MySQL Production DB', type: 'MySQL', latency: '45ms' },
    { name: 'AWS Timestream', type: 'Time Series', latency: '23ms' },
    { name: 'Vector Database', type: 'Semantic Search', latency: '12ms' }
  ];

  constructor() { }
}