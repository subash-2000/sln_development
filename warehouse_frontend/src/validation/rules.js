import * as z from 'zod';

// Standard Indian GSTIN: 2 digits (state) + 5 letters (PAN) + 4 digits + 1 letter + 1 entity code + 'Z' + 1 check digit
export const INDIAN_GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

/**
 * Validates phone numbers:
 * - Minimum 10 digits without country code (e.g. 9876543210 or 0802345678)
 * - With country code prefix '+' (e.g. +91 9876543210 or +919876543210, +1 5551234567)
 * - Allows optional spaces and hyphens
 */
export const validatePhoneNumber = (val) => {
  if (!val || typeof val !== 'string') return false;
  const clean = val.trim();
  if (!clean) return false;
  
  if (clean.startsWith('+')) {
    const compact = clean.replace(/[\s-]/g, '');
    return /^\+\d{1,4}\d{10,14}$/.test(compact);
  }
  
  const compact = clean.replace(/[\s-]/g, '');
  return /^[6-9]\d{9}$|^\d{10,12}$/.test(compact);
};

// Reusable Zod schema for GSTIN (optional/blank allowed, or valid GSTIN)
export const gstinOptionalSchema = z
  .string()
  .optional()
  .or(z.literal(''))
  .refine(
    (val) => !val || val.trim() === '' || INDIAN_GSTIN_REGEX.test(val.trim().toUpperCase()),
    { message: 'Please enter a valid GSTIN' }
  );

// Reusable Zod schema for GSTIN (strictly mandatory)
export const gstinRequiredSchema = z
  .string({ required_error: 'GSTIN is required' })
  .trim()
  .min(1, 'GSTIN is required')
  .refine(
    (val) => INDIAN_GSTIN_REGEX.test(val.trim().toUpperCase()),
    { message: 'Please enter a valid GSTIN' }
  );

// Reusable Zod schema for Phone (optional/blank allowed, or valid phone)
export const phoneOptionalSchema = z
  .string()
  .optional()
  .or(z.literal(''))
  .refine(
    (val) => !val || val.trim() === '' || validatePhoneNumber(val),
    { message: 'Please enter a valid phone number' }
  );

// Reusable Zod schema for Phone (strictly mandatory)
export const phoneRequiredSchema = z
  .string({ required_error: 'Please enter a valid phone number' })
  .trim()
  .min(1, 'Please enter a valid phone number')
  .refine(validatePhoneNumber, {
    message: 'Please enter a valid phone number',
  });

// Reusable Zod schema for Email (optional/blank allowed, or valid email)
export const emailOptionalSchema = z
  .string()
  .email('Invalid email address')
  .optional()
  .or(z.literal(''));

// Reusable Zod schema for Email (strictly mandatory)
export const emailRequiredSchema = z
  .string({ required_error: 'Email address is required' })
  .trim()
  .min(1, 'Email address is required')
  .email('Invalid email address');
