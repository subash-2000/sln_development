import { describe, it, expect } from 'vitest';
import {
  getCompanySchema,
  INDIAN_GSTIN_REGEX,
  validatePhoneNumber,
} from '../../src/modules/companies/schemas/company.schema';

describe('Company Schema Validation - Red Marked Fields', () => {
  const validBaseData = {
    code: 'SLN001',
    name: 'SLN Super Market',
    tax_id: '29ABCDE1234F1Z5',
    address: '123 Main Street, Industrial Layout, Bangalore',
    phone: '9876543210',
  };

  describe('Tax ID / GSTIN Validation', () => {
    it('should pass with a valid 15-character Indian GSTIN', () => {
      const schema = getCompanySchema();
      const result = schema.safeParse(validBaseData);
      expect(result.success).toBe(true);
    });

    it('should fail when tax_id is empty or missing', () => {
      const schema = getCompanySchema();
      const result = schema.safeParse({ ...validBaseData, tax_id: '' });
      expect(result.success).toBe(false);
      expect(result.error.issues.some((i) => i.path.includes('tax_id'))).toBe(true);
    });

    it('should fail when tax_id is invalid format', () => {
      const schema = getCompanySchema();
      const invalidGstins = [
        '12345',
        '29ABCDE1234F1Z', // 14 chars
        '29ABCDE1234F1Z59', // 16 chars
        'INVALIDGSTIN123',
        '29abcde1234f1z#',
      ];

      for (const invalid of invalidGstins) {
        const result = schema.safeParse({ ...validBaseData, tax_id: invalid });
        expect(result.success).toBe(false);
        const taxError = result.error.issues.find((i) => i.path.includes('tax_id'));
        expect(taxError?.message).toContain('valid GSTIN');
      }
    });

    it('should validate standard GSTIN regex directly', () => {
      expect(INDIAN_GSTIN_REGEX.test('29ABCDE1234F1Z5')).toBe(true);
      expect(INDIAN_GSTIN_REGEX.test('27AABCG1234F1Z9')).toBe(true);
      expect(INDIAN_GSTIN_REGEX.test('invalid')).toBe(false);
    });
  });

  describe('Address Validation', () => {
    it('should pass with a valid address >= 5 characters', () => {
      const schema = getCompanySchema();
      const result = schema.safeParse(validBaseData);
      expect(result.success).toBe(true);
    });

    it('should fail when address is empty or whitespace only', () => {
      const schema = getCompanySchema();
      const emptyResult = schema.safeParse({ ...validBaseData, address: '' });
      expect(emptyResult.success).toBe(false);
      expect(emptyResult.error.issues.some((i) => i.path.includes('address'))).toBe(true);

      const spaceResult = schema.safeParse({ ...validBaseData, address: '    ' });
      expect(spaceResult.success).toBe(false);
      expect(spaceResult.error.issues.some((i) => i.path.includes('address'))).toBe(true);
    });

    it('should fail when address is shorter than 5 characters', () => {
      const schema = getCompanySchema();
      const result = schema.safeParse({ ...validBaseData, address: 'Plot' });
      expect(result.success).toBe(false);
      const addressError = result.error.issues.find((i) => i.path.includes('address'));
      expect(addressError?.message).toContain('at least 5 characters');
    });

    it('should fail when address exceeds 500 characters', () => {
      const schema = getCompanySchema();
      const longAddress = 'A'.repeat(501);
      const result = schema.safeParse({ ...validBaseData, address: longAddress });
      expect(result.success).toBe(false);
      const addressError = result.error.issues.find((i) => i.path.includes('address'));
      expect(addressError?.message).toContain('cannot exceed 500 characters');
    });
  });

  describe('Phone Validation', () => {
    it('should pass with valid 10-digit Indian numbers', () => {
      const validPhones = ['9876543210', '8876543210', '7876543210', '6876543210'];
      const schema = getCompanySchema();

      for (const phone of validPhones) {
        const result = schema.safeParse({ ...validBaseData, phone });
        expect(result.success).toBe(true);
      }
    });

    it('should pass with valid country code prefix (+91, +1, etc.)', () => {
      const validPhones = [
        '+91 9876543210',
        '+919876543210',
        '+91-9876543210',
        '+1 5551234567',
        '+44 2071838750',
      ];
      const schema = getCompanySchema();

      for (const phone of validPhones) {
        const result = schema.safeParse({ ...validBaseData, phone });
        expect(result.success).toBe(true);
      }
    });

    it('should fail when phone is empty or whitespace', () => {
      const schema = getCompanySchema();
      const emptyResult = schema.safeParse({ ...validBaseData, phone: '' });
      expect(emptyResult.success).toBe(false);
      expect(emptyResult.error.issues.some((i) => i.path.includes('phone'))).toBe(true);

      const spaceResult = schema.safeParse({ ...validBaseData, phone: '   ' });
      expect(spaceResult.success).toBe(false);
      expect(spaceResult.error.issues.some((i) => i.path.includes('phone'))).toBe(true);
    });

    it('should fail when phone has invalid characters or fewer than 10 digits', () => {
      const invalidPhones = ['12345', 'abcdefghij', '98765', 'phone12345'];
      const schema = getCompanySchema();

      for (const phone of invalidPhones) {
        const result = schema.safeParse({ ...validBaseData, phone });
        expect(result.success).toBe(false);
        const phoneError = result.error.issues.find((i) => i.path.includes('phone'));
        expect(phoneError?.message).toContain('valid phone number');
      }
    });

    it('should test validatePhoneNumber helper directly', () => {
      expect(validatePhoneNumber('9876543210')).toBe(true);
      expect(validatePhoneNumber('+91 9876543210')).toBe(true);
      expect(validatePhoneNumber('')).toBe(false);
      expect(validatePhoneNumber(null)).toBe(false);
      expect(validatePhoneNumber('123')).toBe(false);
    });
  });

  describe('Duplicate Validation across the 4 fields with already created company data', () => {
    const existingCompanies = [
      {
        id: 'cmp-100',
        code: 'SLN 001',
        name: 'SLN super market 001',
        registration_number: 'CIN12345',
        tax_id: '29ABCDE1234F1Z5',
      },
      {
        id: 'cmp-200',
        code: 'SLN 002',
        name: 'SLN super market 002',
        registration_number: 'CIN67890',
        tax_id: '27AABCG1234F1Z9',
      },
    ];

    it('should fail when Company Code matches another company', () => {
      const schema = getCompanySchema(false, existingCompanies);
      const result = schema.safeParse({
        ...validBaseData,
        code: 'sln 001', // case insensitive check
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('code'));
      expect(error?.message).toBe('Company Code already exists with another company');
    });

    it('should fail when Company Name matches another company', () => {
      const schema = getCompanySchema(false, existingCompanies);
      const result = schema.safeParse({
        ...validBaseData,
        name: 'SLN SUPER MARKET 001',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('name'));
      expect(error?.message).toBe('Company Name already exists with another company');
    });

    it('should fail when Registration Number matches another company', () => {
      const schema = getCompanySchema(false, existingCompanies);
      const result = schema.safeParse({
        ...validBaseData,
        registration_number: 'cin12345',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('registration_number'));
      expect(error?.message).toBe('Registration Number already exists with another company');
    });

    it('should fail when Tax ID / GSTIN matches another company', () => {
      const schema = getCompanySchema(false, existingCompanies);
      const result = schema.safeParse({
        ...validBaseData,
        tax_id: '29ABCDE1234F1Z5',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('tax_id'));
      expect(error?.message).toBe('Tax ID / GSTIN already exists with another company');
    });

    it('should pass on edit when data matches the current company being edited', () => {
      // Editing cmp-100 keeping its own code, name, reg number, and tax_id
      const schema = getCompanySchema(true, existingCompanies, 'cmp-100');
      const result = schema.safeParse({
        ...validBaseData,
        code: 'SLN 001',
        name: 'SLN super market 001',
        registration_number: 'CIN12345',
        tax_id: '29ABCDE1234F1Z5',
      });
      expect(result.success).toBe(true);
    });

    it('should fail on edit when data matches ANOTHER company', () => {
      // Editing cmp-100 but using cmp-200's GSTIN
      const schema = getCompanySchema(true, existingCompanies, 'cmp-100');
      const result = schema.safeParse({
        ...validBaseData,
        code: 'SLN 001',
        name: 'SLN super market 001',
        registration_number: 'CIN12345',
        tax_id: '27AABCG1234F1Z9', // matches cmp-200
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('tax_id'));
      expect(error?.message).toBe('Tax ID / GSTIN already exists with another company');
    });
  });
});
