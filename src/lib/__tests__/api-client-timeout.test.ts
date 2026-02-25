import { describe, it, expect } from 'vitest';
import { AI_REQUEST_TIMEOUT } from '../api-client';

describe('API client timeout config', () => {
  it('uses an extended AI timeout for long-running chat/tool responses', () => {
    expect(AI_REQUEST_TIMEOUT).toBe(180000);
  });
});
