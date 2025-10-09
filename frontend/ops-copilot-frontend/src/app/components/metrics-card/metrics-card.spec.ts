import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetricsCard } from './metrics-card';

describe('MetricsCard', () => {
  let component: MetricsCard;
  let fixture: ComponentFixture<MetricsCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetricsCard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MetricsCard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
