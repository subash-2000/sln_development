import { describe, it, expect } from 'vitest';
import { branchSchema, getBranchSchema } from '../../src/modules/branches/schemas/branch.schema';

describe('Branch Schema Validation', () => {
  const validBaseBranch = {
    company_id: 'cmp-01',
    code: 'BR-01',
    name: 'Mumbai Central Branch',
    tax_id: '27ABCDE1234F1Z5',
    address: 'Andheri East, Mumbai',
    phone: '+91 9876543210',
    email: 'mumbai@company.com',
    is_active: true,
  };

  it('should validate valid branch data', () => {
    const result = branchSchema.safeParse(validBaseBranch);
    expect(result.success).toBe(true);
  });

  it('should accept blank/optional Tax ID / GSTIN, phone, and email', () => {
    const result = branchSchema.safeParse({
      company_id: 'cmp-01',
      code: 'BR-02',
      name: 'Delhi Branch',
      tax_id: '',
      phone: '',
      email: '',
      is_active: true,
    });
    expect(result.success).toBe(true);
  });

  describe('Tax ID / GSTIN Validation', () => {
    it('should reject invalid GSTIN format', () => {
      const result = branchSchema.safeParse({
        ...validBaseBranch,
        tax_id: '1234INVALID',
      });
      expect(result.success).toBe(false);
      const taxError = result.error.issues.find((i) => i.path.includes('tax_id'));
      expect(taxError).toBeDefined();
      expect(taxError.message).toBe('Please enter a valid GSTIN');
    });

    it('should accept valid GSTIN', () => {
      const result = branchSchema.safeParse({
        ...validBaseBranch,
        tax_id: '27ABCDE1234F1Z5',
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Phone Number Validation', () => {
    it('should reject invalid phone numbers', () => {
      const result = branchSchema.safeParse({
        ...validBaseBranch,
        phone: 'invalid_phone',
      });
      expect(result.success).toBe(false);
      const phoneError = result.error.issues.find((i) => i.path.includes('phone'));
      expect(phoneError).toBeDefined();
      expect(phoneError.message).toBe('Please enter a valid phone number');
    });

    it('should accept 10-digit valid phone', () => {
      const result = branchSchema.safeParse({
        ...validBaseBranch,
        phone: '9876543210',
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Email Validation', () => {
    it('should reject invalid email format', () => {
      const result = branchSchema.safeParse({
        ...validBaseBranch,
        email: 'bad-email',
      });
      expect(result.success).toBe(false);
      const emailError = result.error.issues.find((i) => i.path.includes('email'));
      expect(emailError).toBeDefined();
      expect(emailError.message).toBe('Invalid email address');
    });
  });

  describe('Duplicate Branch Code and Name Uniqueness', () => {
    const existingBranches = [
      { id: 'br-1', code: 'BR-01', name: 'Mumbai Central Branch' },
      { id: 'br-2', code: 'BR-02', name: 'Delhi Branch' },
    ];

    it('should reject duplicate branch code during create', () => {
      const schema = getBranchSchema(false, existingBranches);
      const result = schema.safeParse({
        ...validBaseBranch,
        code: 'br-01', // case-insensitive match
        name: 'Pune Branch',
      });
      expect(result.success).toBe(false);
      const codeError = result.error.issues.find((i) => i.path.includes('code'));
      expect(codeError).toBeDefined();
      expect(codeError.message).toBe('Branch Code already exists with another branch');
    });

    it('should reject duplicate branch name during create', () => {
      const schema = getBranchSchema(false, existingBranches);
      const result = schema.safeParse({
        ...validBaseBranch,
        code: 'BR-99',
        name: 'mumbai central branch', // case-insensitive match
      });
      expect(result.success).toBe(false);
      const nameError = result.error.issues.find((i) => i.path.includes('name'));
      expect(nameError).toBeDefined();
      expect(nameError.message).toBe('Branch Name already exists with another branch');
    });

    it('should allow current branch to retain its code and name during edit', () => {
      const schema = getBranchSchema(true, existingBranches, 'br-1');
      const result = schema.safeParse({
        ...validBaseBranch,
        code: 'BR-01',
        name: 'Mumbai Central Branch',
      });
      expect(result.success).toBe(true);
    });

    it('should reject updating to another branch code or name during edit', () => {
      const schema = getBranchSchema(true, existingBranches, 'br-1');
      const result = schema.safeParse({
        ...validBaseBranch,
        code: 'BR-02', // matches br-2
        name: 'Unique Name',
      });
      expect(result.success).toBe(false);
      const codeError = result.error.issues.find((i) => i.path.includes('code'));
      expect(codeError).toBeDefined();
      expect(codeError.message).toBe('Branch Code already exists with another branch');
    });
  });
});

