import { describe, it, expect, vi } from 'vitest';
import { normalizeError } from '../../src/services/api/errors';

describe('API Client Error Normalization', () => {
  it('should normalize response errors correctly', () => {
    const mockError = {
      response: {
        status: 400,
        headers: { 'x-request-id': 'req-123' },
        data: {
          message: 'Invalid input',
          error_code: 'VALIDATION_ERROR',
          details: { field: 'required' }
        }
      }
    };

    const normalized = normalizeError(mockError);

    expect(normalized.status).toBe(400);
    expect(normalized.message).toBe('Invalid input');
    expect(normalized.requestId).toBe('req-123');
    expect(normalized.code).toBe('VALIDATION_ERROR');
  });

  it('should handle network errors', () => {
    const mockError = {
      request: {}
    };

    const normalized = normalizeError(mockError);

    expect(normalized.code).toBe('NETWORK_ERROR');
    expect(normalized.status).toBe(0);
  });
});
