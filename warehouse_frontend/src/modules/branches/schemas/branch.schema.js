import * as z from 'zod';
import {
  INDIAN_GSTIN_REGEX,
  validatePhoneNumber,
  gstinOptionalSchema,
  phoneOptionalSchema,
  emailOptionalSchema,
} from '../../../validation/rules';

export const branchSchema = z.object({
  company_id: z.string({ required_error: 'Please select a company' }).min(1, 'Please select a company'),
  code: z
    .string({ required_error: 'Branch Code is required' })
    .trim()
    .min(2, 'Code must be at least 2 characters')
    .max(20, 'Code cannot exceed 20 characters'),
  name: z
    .string({ required_error: 'Branch Name is required' })
    .trim()
    .min(2, 'Name must be at least 2 characters')
    .max(100, 'Name cannot exceed 100 characters'),
  tax_id: gstinOptionalSchema,
  address: z.string().optional().or(z.literal('')),
  phone: phoneOptionalSchema,
  email: emailOptionalSchema,
  is_active: z.boolean().default(true),
});

export const getBranchSchema = (isEdit = false, existingBranches = [], currentBranchId = null) =>
  branchSchema.extend({
    code: z
      .string({ required_error: 'Branch Code is required' })
      .trim()
      .min(2, 'Code must be at least 2 characters')
      .max(20, 'Code cannot exceed 20 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toUpperCase();
          return !existingBranches.some(
            (b) => b.id !== currentBranchId && b.code?.trim().toUpperCase() === clean
          );
        },
        {
          message: 'Branch Code already exists with another branch',
        }
      ),
    name: z
      .string({ required_error: 'Branch Name is required' })
      .trim()
      .min(2, 'Name must be at least 2 characters')
      .max(100, 'Name cannot exceed 100 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toLowerCase();
          return !existingBranches.some(
            (b) => b.id !== currentBranchId && b.name?.trim().toLowerCase() === clean
          );
        },
        {
          message: 'Branch Name already exists with another branch',
        }
      ),
  });

export { INDIAN_GSTIN_REGEX, validatePhoneNumber };
