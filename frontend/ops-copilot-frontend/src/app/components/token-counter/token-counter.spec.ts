import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenCounterComponent } from './token-counter';
import { ApiService } from '../../services/api';
import { of } from 'rxjs';

describe('TokenCounterComponent', () => {
  let component: TokenCounterComponent;
  let fixture: ComponentFixture<TokenCounterComponent>;
  let mockApiService: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    const apiServiceSpy = jasmine.createSpyObj('ApiService', ['getUsageStats', 'getSystemStats']);

    await TestBed.configureTestingModule({
      imports: [TokenCounterComponent],
      providers: [
        { provide: ApiService, useValue: apiServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenCounterComponent);
    component = fixture.componentInstance;
    mockApiService = TestBed.inject(ApiService) as jasmine.SpyObj<ApiService>;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show no token message when no token provided', () => {
    component.apiToken = null;
    fixture.detectChanges();
    
    const compiled = fixture.nativeElement;
    expect(compiled.textContent).toContain('No API token provided');
  });

  it('should load usage stats when token is provided', () => {
    const mockStats = {
      user_id: 'test_user',
      role: 'user',
      total_requests: 10,
      daily_requests: 5,
      total_tokens: 1,
      last_reset: '2024-01-15',
      tokens: []
    };

    mockApiService.getUsageStats.and.returnValue(of(mockStats));
    
    component.apiToken = 'test_token';
    component.ngOnInit();
    
    expect(mockApiService.getUsageStats).toHaveBeenCalledWith('test_token');
  });
});
