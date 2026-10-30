import * as z from 'zod';
import { phoneOptionalSchema, validatePhoneNumber } from '../../../validation/rules';

export const warehouseSchema = z.object({
  company_id: z.string().min(1, 'Company is required'),
  branch_id: z.string().optional().nullable().or(z.literal('')),
  code: z.string().min(1, 'Warehouse code is required').max(50, 'Code cannot exceed 50 characters'),
  name: z.string().min(1, 'Warehouse name is required').max(255, 'Name cannot exceed 255 characters'),
  warehouse_type: z.enum([
    'OWNED',
    'LEASED',
    'BONDED',
    'THIRD_PARTY',
    'VENDOR',
    'VIRTUAL'
  ], { required_error: 'Please select a warehouse type' }),
  address: z.string().max(255, 'Address cannot exceed 255 characters').optional().nullable().or(z.literal('')),
  city: z.string().max(100, 'City cannot exceed 100 characters').optional().nullable().or(z.literal('')),
  state: z.string().max(100, 'State cannot exceed 100 characters').optional().nullable().or(z.literal('')),
  contact_person: z.string().max(255, 'Contact person cannot exceed 255 characters').optional().nullable().or(z.literal('')),
  phone: phoneOptionalSchema,
  is_active: z.boolean().default(true),
});

export { validatePhoneNumber };
