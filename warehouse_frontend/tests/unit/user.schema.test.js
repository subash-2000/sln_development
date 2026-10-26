import { describe, it, expect } from 'vitest';
import { createUserSchema, editUserSchema, userSchema } from '../../src/modules/users/schemas/user.schema';

describe('User Schema Validation', () => {
  const validUserData = {
    username: 'johndoe',
    email: 'john@example.com',
    name: 'John Doe',
    password: 'secretpassword123',
    role_id: 'role_1',
    company_ids: ['cmp_1'],
    is_active: true,
  };

  describe('createUserSchema (Mandatory Password)', () => {
    it('should validate valid user data with complete password', () => {
      const result = createUserSchema.safeParse(validUserData);
      expect(result.success).toBe(true);
    });

    it('should fail when password is empty string', () => {
      const result = createUserSchema.safeParse({ ...validUserData, password: '' });
      expect(result.success).toBe(false);
      const passwordIssue = result.error.issues.find((i) => i.path.includes('password'));
      expect(passwordIssue).toBeDefined();
      expect(passwordIssue.message).toBe('Password is required');
    });

    it('should fail when password is missing/undefined', () => {
      const { password, ...withoutPassword } = validUserData;
      const result = createUserSchema.safeParse(withoutPassword);
      expect(result.success).toBe(false);
      const passwordIssue = result.error.issues.find((i) => i.path.includes('password'));
      expect(passwordIssue).toBeDefined();
    });

    it('should fail when password is shorter than 6 characters', () => {
      const result = createUserSchema.safeParse({ ...validUserData, password: '123' });
      expect(result.success).toBe(false);
      const passwordIssue = result.error.issues.find((i) => i.path.includes('password'));
      expect(passwordIssue).toBeDefined();
      expect(passwordIssue.message).toBe('Password must be at least 6 characters');
    });

    it('should enforce password as mandatory via default export userSchema', () => {
      const result = userSchema.safeParse({ ...validUserData, password: '' });
      expect(result.success).toBe(false);
      const passwordIssue = result.error.issues.find((i) => i.path.includes('password'));
      expect(passwordIssue).toBeDefined();
      expect(passwordIssue.message).toBe('Password is required');
    });
  });

  describe('editUserSchema (Optional Password)', () => {
    it('should allow empty string password when editing', () => {
      const result = editUserSchema.safeParse({ ...validUserData, password: '' });
      expect(result.success).toBe(true);
    });

    it('should allow omitted password when editing', () => {
      const { password, ...withoutPassword } = validUserData;
      const result = editUserSchema.safeParse(withoutPassword);
      expect(result.success).toBe(true);
    });

    it('should still enforce minimum 6 characters if a new password is provided', () => {
      const result = editUserSchema.safeParse({ ...validUserData, password: '123' });
      expect(result.success).toBe(false);
      const passwordIssue = result.error.issues.find((i) => i.path.includes('password'));
      expect(passwordIssue).toBeDefined();
      expect(passwordIssue.message).toBe('Password must be at least 6 characters');
    });
  });
});
