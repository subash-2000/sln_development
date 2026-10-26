import * as z from 'zod';
import { INDIAN_GSTIN_REGEX, validatePhoneNumber } from '../../companies/schemas/company.schema';

export const getSupplierSchema = (isEdit = false, existingSuppliers = [], currentSupplierId = null) =>
  z.object({
    code: z
      .string({ required_error: 'Supplier Code is required' })
      .trim()
      .min(2, 'Supplier Code must be at least 2 characters')
      .max(50, 'Supplier Code cannot exceed 50 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toUpperCase();
          return !existingSuppliers.some(
            (v) => v.id !== currentSupplierId && v.code?.trim().toUpperCase() === clean
          );
        },
        {
          message: 'Supplier Code already exists with another supplier',
        }
      ),
    name: z
      .string({ required_error: 'Supplier Name is required' })
      .trim()
      .min(2, 'Supplier Name must be at least 2 characters')
      .max(100, 'Supplier Name cannot exceed 100 characters')
      .refine(
        (val) => {
          if (!val) return true;
          const clean = val.trim().toLowerCase();
          return !existingSuppliers.some(
            (v) => v.id !== currentSupplierId && v.name?.trim().toLowerCase() === clean
          );
        },
        {
          message: 'Supplier Name already exists with another supplier',
        }
      ),
    gstin: z
      .string({ required_error: 'GSTIN is required' })
      .trim()
      .min(1, 'GSTIN is required')
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
          return !existingSuppliers.some(
            (v) => v.id !== currentSupplierId && v.gstin && v.gstin.trim().toUpperCase() === clean
          );
        },
        {
          message: 'GSTIN already exists with another supplier',
        }
      ),
    contact_person: z.string().optional().or(z.literal('')),
    phone: z
      .string({ required_error: 'Please enter a valid phone number' })
      .trim()
      .min(1, 'Please enter a valid phone number')
      .refine(validatePhoneNumber, {
        message: 'Please enter a valid phone number',
      })
      .refine(
        (val) => {
          if (!val || val.trim() === '') return true;
          const clean = val.trim().replace(/[\s-]/g, '');
          return !existingSuppliers.some(
            (v) =>
              v.id !== currentSupplierId &&
              v.phone &&
              v.phone.trim().replace(/[\s-]/g, '') === clean
          );
        },
        {
          message: 'Phone number already exists with another supplier',
        }
      ),
    email: z.string().email('Invalid email address').optional().or(z.literal('')),
    address: z
      .string({ required_error: 'Address is required' })
      .trim()
      .min(1, 'Address is required')
      .min(5, 'Address must be at least 5 characters')
      .max(500, 'Address cannot exceed 500 characters'),
    invoice_workflow: z
      .enum(['STANDARD', 'JOB_WORK', 'DIRECT_INVOICE', 'BOTH'])
      .optional()
      .default('STANDARD'),
    is_active: z.boolean().default(true),
  });

export const supplierSchema = getSupplierSchema(false);
/** @deprecated use getSupplierSchema */
export const getVendorSchema = getSupplierSchema;
export const vendorSchema = supplierSchema;
