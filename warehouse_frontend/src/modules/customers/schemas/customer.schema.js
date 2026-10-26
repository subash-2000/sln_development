import * as z from 'zod';
import {
  INDIAN_GSTIN_REGEX,
  validatePhoneNumber,
  gstinOptionalSchema,
  phoneOptionalSchema,
  emailOptionalSchema,
} from '../../../validation/rules';

export const customerSchema = z.object({
  code: z
    .string({ required_error: 'Customer Code is required' })
    .trim()
    .min(2, 'Customer Code must be at least 2 characters')
    .max(50, 'Customer Code cannot exceed 50 characters'),
  name: z
    .string({ required_error: 'Customer Name is required' })
    .trim()
    .min(2, 'Customer Name must be at least 2 characters')
    .max(100, 'Customer Name cannot exceed 100 characters'),
  gstin: gstinOptionalSchema,
  contact_person: z.string().optional().or(z.literal('')),
  phone: phoneOptionalSchema,
  email: emailOptionalSchema,
  address: z.string().optional().or(z.literal('')),
  is_active: z.boolean().default(true),
});

export const getCustomerSchema = (isEdit = false, existingCustomers = [], currentCustomerId = null) =>
  customerSchema.extend({
    code: z
      .string({ required_error: 'Customer Code is required' })
      .trim()
      .min(2, 'Customer Code must be at least 2 characters')
      .max(50, 'Customer Code cannot exceed 50 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toUpperCase();
          return !existingCustomers.some(
            (c) => c.id !== currentCustomerId && c.code?.trim().toUpperCase() === clean
          );
        },
        {
          message: 'Customer Code already exists with another customer',
        }
      ),
  });

export { INDIAN_GSTIN_REGEX, validatePhoneNumber };
