import * as z from 'zod';
import { INDIAN_GSTIN_REGEX, validatePhoneNumber } from '../../../validation/rules';

export { INDIAN_GSTIN_REGEX, validatePhoneNumber };

export const getCompanySchema = (isEdit = false, existingCompanies = [], currentCompanyId = null) =>
  z.object({
    code: z
      .string({ required_error: 'Company Code is required' })
      .trim()
      .min(2, 'Company Code must be at least 2 characters')
      .max(20, 'Company Code cannot exceed 20 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toUpperCase();
          return !existingCompanies.some(
            (c) =>
              c.id !== currentCompanyId &&
              c.code?.trim().toUpperCase() === clean
          );
        },
        {
          message: 'Company Code already exists with another company',
        }
      ),
    name: z
      .string({ required_error: 'Company Name is required' })
      .trim()
      .min(2, 'Company Name must be at least 2 characters')
      .max(100, 'Company Name cannot exceed 100 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toLowerCase();
          return !existingCompanies.some(
            (c) =>
              c.id !== currentCompanyId &&
              c.name?.trim().toLowerCase() === clean
          );
        },
        {
          message: 'Company Name already exists with another company',
        }
      ),
    registration_number: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine(
        (val) => {
          if (!val || val.trim() === '') return true;
          const clean = val.trim().toLowerCase();
          return !existingCompanies.some(
            (c) =>
              c.id !== currentCompanyId &&
              c.registration_number &&
              c.registration_number.trim().toLowerCase() === clean
          );
        },
        {
          message: 'Registration Number already exists with another company',
        }
      ),
    tax_id: z
      .string({ required_error: 'Tax ID / GSTIN is required' })
      .trim()
      .min(1, 'Tax ID / GSTIN is required')
      .refine(
        (val) => INDIAN_GSTIN_REGEX.test(val.trim().toUpperCase()),
        {
          message: 'Please enter a valid GSTIN',
        }
      )
      .refine(
        (val) => {
          if (!val || val.trim() === '') return true;
          const clean = val.trim().toUpperCase();
          return !existingCompanies.some(
            (c) =>
              c.id !== currentCompanyId &&
              (c.tax_id || c.gstin) &&
              (c.tax_id || c.gstin).trim().toUpperCase() === clean
          );
        },
        {
          message: 'Tax ID / GSTIN already exists with another company',
        }
      ),
    address: z
      .string({ required_error: 'Address is required' })
      .trim()
      .min(1, 'Address is required')
      .min(5, 'Address must be at least 5 characters')
      .max(500, 'Address cannot exceed 500 characters'),
    phone: z
      .string({ required_error: 'Please enter a valid phone number' })
      .trim()
      .min(1, 'Please enter a valid phone number')
      .refine(validatePhoneNumber, {
        message: 'Please enter a valid phone number',
      }),
    email: z.string().email('Invalid email address').optional().or(z.literal('')),
    website: z.string().url('Invalid URL').optional().or(z.literal('')),
    is_active: z.boolean().default(true),
  });

export const companySchema = getCompanySchema(false);

