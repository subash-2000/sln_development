import { describe, it, expect } from 'vitest';
import { isEntityActive, getStatusVariant } from '../../src/constants/status';

describe('status utilities', () => {
  describe('isEntityActive', () => {
    it('returns true when status is ACTIVE even if is_active is missing', () => {
      expect(isEntityActive({ status: 'ACTIVE' })).toBe(true);
      expect(isEntityActive({ status: 'active' })).toBe(true);
    });

    it('returns false when status is INACTIVE even if is_active is true', () => {
      expect(isEntityActive({ status: 'INACTIVE', is_active: true })).toBe(false);
      expect(isEntityActive({ status: 'inactive', is_active: true })).toBe(false);
    });

    it('falls back to is_active when status is not provided', () => {
      expect(isEntityActive({ is_active: true })).toBe(true);
      expect(isEntityActive({ is_active: false })).toBe(false);
    });

    it('returns false for null or undefined', () => {
      expect(isEntityActive(null)).toBe(false);
      expect(isEntityActive(undefined)).toBe(false);
    });
  });

  describe('getStatusVariant', () => {
    it('returns success for ACTIVE and neutral for INACTIVE', () => {
      expect(getStatusVariant('ACTIVE')).toBe('success');
      expect(getStatusVariant('INACTIVE')).toBe('neutral');
    });
  });
});
