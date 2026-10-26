import { describe, it, expect } from 'vitest';
import { customerSchema, getCustomerSchema } from '../../src/modules/customers/schemas/customer.schema';

describe('Customer Schema Validation', () => {
  const validBaseCustomer = {
    code: 'CUST-001',
    name: 'Acme Traders',
    gstin: '29ABCDE1234F1Z5',
    contact_person: 'John Doe',
    phone: '+91 9876543210',
    email: 'acme@example.com',
    address: '123 Market Street, Bengaluru',
    is_active: true,
  };

  it('should validate valid customer data', () => {
    const result = customerSchema.safeParse(validBaseCustomer);
    expect(result.success).toBe(true);
  });

  it('should accept blank/optional GSTIN, phone, and email', () => {
    const result = customerSchema.safeParse({
      code: 'CUST-002',
      name: 'Retail Customer',
      gstin: '',
      phone: '',
      email: '',
      is_active: true,
    });
    expect(result.success).toBe(true);
  });

  describe('GSTIN Validation', () => {
    it('should reject invalid GSTIN format', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        gstin: 'INVALIDGSTIN123',
      });
      expect(result.success).toBe(false);
      const gstinError = result.error.issues.find((i) => i.path.includes('gstin'));
      expect(gstinError).toBeDefined();
      expect(gstinError.message).toBe('Please enter a valid GSTIN');
    });

    it('should accept valid GSTIN with lowercase letters and normalize or validate properly', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        gstin: '29abcde1234f1z5',
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Phone Number Validation', () => {
    it('should accept standard 10-digit Indian phone number', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        phone: '9876543210',
      });
      expect(result.success).toBe(true);
    });

    it('should accept international format phone number with +', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        phone: '+91 98765 43210',
      });
      expect(result.success).toBe(true);
    });

    it('should reject invalid phone numbers', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        phone: '12345',
      });
      expect(result.success).toBe(false);
      const phoneError = result.error.issues.find((i) => i.path.includes('phone'));
      expect(phoneError).toBeDefined();
      expect(phoneError.message).toBe('Please enter a valid phone number');
    });
  });

  describe('Email Validation', () => {
    it('should reject invalid email format', () => {
      const result = customerSchema.safeParse({
        ...validBaseCustomer,
        email: 'invalid-email-address',
      });
      expect(result.success).toBe(false);
      const emailError = result.error.issues.find((i) => i.path.includes('email'));
      expect(emailError).toBeDefined();
      expect(emailError.message).toBe('Invalid email address');
    });
  });
});
