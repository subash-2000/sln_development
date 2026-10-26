import { describe, it, expect } from 'vitest';
import { getVendorSchema } from '../../src/modules/vendors/schemas/vendor.schema';
import { INDIAN_GSTIN_REGEX, validatePhoneNumber } from '../../src/modules/companies/schemas/company.schema';

describe('Vendor Schema Validation - Required Fields and Duplicate Checks', () => {
  const validBaseData = {
    code: 'VND001',
    name: 'Acme Industrial Supplies',
    gstin: '29ABCDE1234F1Z5',
    phone: '9876543210',
    address: '123 Main Industrial Estate, Peenya, Bangalore',
    contact_person: 'John Doe',
    email: 'vendor@example.com',
    is_active: true,
  };

  describe('GSTIN Validation', () => {
    it('should pass with a valid 15-character Indian GSTIN', () => {
      const schema = getVendorSchema();
      const result = schema.safeParse(validBaseData);
      expect(result.success).toBe(true);
    });

    it('should fail when gstin is empty or missing', () => {
      const schema = getVendorSchema();
      const result = schema.safeParse({ ...validBaseData, gstin: '' });
      expect(result.success).toBe(false);
      expect(result.error.issues.some((i) => i.path.includes('gstin'))).toBe(true);
    });

    it('should fail when gstin is invalid format', () => {
      const schema = getVendorSchema();
      const invalidGstins = [
        '12345',
        '29ABCDE1234F1Z', // 14 chars
        '29ABCDE1234F1Z59', // 16 chars
        'INVALIDGSTIN123',
        '29abcde1234f1z#',
      ];

      for (const invalid of invalidGstins) {
        const result = schema.safeParse({ ...validBaseData, gstin: invalid });
        expect(result.success).toBe(false);
        const gstinError = result.error.issues.find((i) => i.path.includes('gstin'));
        expect(gstinError?.message).toContain('valid GSTIN');
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
      const schema = getVendorSchema();
      const result = schema.safeParse(validBaseData);
      expect(result.success).toBe(true);
    });

    it('should fail when address is empty or whitespace only', () => {
      const schema = getVendorSchema();
      const emptyResult = schema.safeParse({ ...validBaseData, address: '' });
      expect(emptyResult.success).toBe(false);
      expect(emptyResult.error.issues.some((i) => i.path.includes('address'))).toBe(true);

      const spaceResult = schema.safeParse({ ...validBaseData, address: '    ' });
      expect(spaceResult.success).toBe(false);
      expect(spaceResult.error.issues.some((i) => i.path.includes('address'))).toBe(true);
    });

    it('should fail when address is shorter than 5 characters', () => {
      const schema = getVendorSchema();
      const result = schema.safeParse({ ...validBaseData, address: 'Plot' });
      expect(result.success).toBe(false);
      const addressError = result.error.issues.find((i) => i.path.includes('address'));
      expect(addressError?.message).toContain('at least 5 characters');
    });

    it('should fail when address exceeds 500 characters', () => {
      const schema = getVendorSchema();
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
      const schema = getVendorSchema();

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
      const schema = getVendorSchema();

      for (const phone of validPhones) {
        const result = schema.safeParse({ ...validBaseData, phone });
        expect(result.success).toBe(true);
      }
    });

    it('should fail when phone is empty or whitespace', () => {
      const schema = getVendorSchema();
      const emptyResult = schema.safeParse({ ...validBaseData, phone: '' });
      expect(emptyResult.success).toBe(false);
      expect(emptyResult.error.issues.some((i) => i.path.includes('phone'))).toBe(true);

      const spaceResult = schema.safeParse({ ...validBaseData, phone: '   ' });
      expect(spaceResult.success).toBe(false);
      expect(spaceResult.error.issues.some((i) => i.path.includes('phone'))).toBe(true);
    });

    it('should fail when phone has invalid characters or fewer than 10 digits', () => {
      const invalidPhones = ['12345', 'abcdefghij', '98765', 'phone12345'];
      const schema = getVendorSchema();

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

  describe('Duplicate Validation across the 4 fields with already created vendor data', () => {
    const existingVendors = [
      {
        id: 'vnd-100',
        code: 'VND 001',
        name: 'Apex Supplies 001',
        gstin: '29ABCDE1234F1Z5',
        phone: '9876543210',
      },
      {
        id: 'vnd-200',
        code: 'VND 002',
        name: 'Apex Supplies 002',
        gstin: '27AABCG1234F1Z9',
        phone: '+91 9123456780',
      },
    ];

    it('should fail when Vendor Code matches another vendor', () => {
      const schema = getVendorSchema(false, existingVendors);
      const result = schema.safeParse({
        ...validBaseData,
        code: 'vnd 001', // case insensitive check
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('code'));
      expect(error?.message).toBe('Vendor Code already exists with another vendor');
    });

    it('should fail when Vendor Name matches another vendor', () => {
      const schema = getVendorSchema(false, existingVendors);
      const result = schema.safeParse({
        ...validBaseData,
        name: 'APEX SUPPLIES 001',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('name'));
      expect(error?.message).toBe('Vendor Name already exists with another vendor');
    });

    it('should fail when GSTIN matches another vendor', () => {
      const schema = getVendorSchema(false, existingVendors);
      const result = schema.safeParse({
        ...validBaseData,
        gstin: '29ABCDE1234F1Z5',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('gstin'));
      expect(error?.message).toBe('GSTIN already exists with another vendor');
    });

    it('should fail when Phone Number matches another vendor', () => {
      const schema = getVendorSchema(false, existingVendors);
      const result = schema.safeParse({
        ...validBaseData,
        phone: '9876543210',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('phone'));
      expect(error?.message).toBe('Phone number already exists with another vendor');
    });

    it('should pass on edit when data matches the current vendor being edited', () => {
      // Editing vnd-100 keeping its own code, name, gstin, and phone
      const schema = getVendorSchema(true, existingVendors, 'vnd-100');
      const result = schema.safeParse({
        ...validBaseData,
        code: 'VND 001',
        name: 'Apex Supplies 001',
        gstin: '29ABCDE1234F1Z5',
        phone: '9876543210',
      });
      expect(result.success).toBe(true);
    });

    it('should fail on edit when data matches ANOTHER vendor', () => {
      // Editing vnd-100 but using vnd-200's GSTIN
      const schema = getVendorSchema(true, existingVendors, 'vnd-100');
      const result = schema.safeParse({
        ...validBaseData,
        code: 'VND 001',
        name: 'Apex Supplies 001',
        gstin: '27AABCG1234F1Z9', // matches vnd-200
        phone: '9876543210',
      });
      expect(result.success).toBe(false);
      const error = result.error.issues.find((i) => i.path.includes('gstin'));
      expect(error?.message).toBe('GSTIN already exists with another vendor');
    });
  });
});
