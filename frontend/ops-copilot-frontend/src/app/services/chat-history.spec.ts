import { TestBed } from '@angular/core/testing';

import { ChatHistory } from './chat-history';

describe('ChatHistory', () => {
  let service: ChatHistory;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChatHistory);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
