import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StatusSidebar } from './status-sidebar';

describe('StatusSidebar', () => {
  let component: StatusSidebar;
  let fixture: ComponentFixture<StatusSidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusSidebar]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StatusSidebar);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
