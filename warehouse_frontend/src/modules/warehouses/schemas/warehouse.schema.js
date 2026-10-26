import * as z from 'zod';
import { phoneOptionalSchema, validatePhoneNumber } from '../../../validation/rules';

export const warehouseSchema = z.object({
  company_id: z.string().min(1, 'Company required'),
  branch_id: z.string().min(1, 'Branch required'),
  code: z.string().min(3, 'Code required').max(50),
  name: z.string().min(2, 'Name required').max(200),
  warehouse_type: z.enum(['OWNED', 'LEASED', 'VENDOR']),
  address: z.string().optional().or(z.literal('')),
  city: z.string().min(2, 'City required'),
  state: z.string().min(2, 'State required'),
  contact_person: z.string().optional().or(z.literal('')),
  phone: phoneOptionalSchema,
  is_active: z.boolean().default(true),
});

export { validatePhoneNumber };
