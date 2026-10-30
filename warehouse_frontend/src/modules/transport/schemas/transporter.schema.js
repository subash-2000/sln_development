import { z } from 'zod';
import { phoneOptionalSchema } from '../../../validation/rules';

export const transporterSchema = z.object({
  code: z.string().min(2, 'Code is required').max(50),
  name: z.string().min(2, 'Name is required').max(255),
  gstin: z.string().max(15).optional().or(z.literal('')),
  pan: z.string().length(10).optional().or(z.literal('')),
  contact_person: z.string().max(255).optional().or(z.literal('')),
  phone: phoneOptionalSchema,
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  address: z.string().optional().or(z.literal('')),
  city: z.string().max(100).optional().or(z.literal('')),
  state: z.string().max(100).optional().or(z.literal('')),
  pincode: z.string().max(20).optional().or(z.literal('')),
  vehicle_number: z.string().max(50).optional().or(z.literal('')),
  vehicle_type: z.string().max(50).optional().or(z.literal('')),
  driver_name: z.string().max(100).optional().or(z.literal('')),
  driver_phone: phoneOptionalSchema,
  status: z.enum(['ACTIVE', 'INACTIVE']).optional(),
});

export const vehicleSchema = z.object({
  vehicle_number: z.string().min(2, 'Vehicle number is required').max(50),
  vehicle_type: z.string().max(50).optional().or(z.literal('')),
  driver_name: z.string().max(100).optional().or(z.literal('')),
  driver_phone: phoneOptionalSchema,
  capacity: z.string().max(50).optional().or(z.literal('')),
  rc_number: z.string().max(50).optional().or(z.literal('')),
  is_default: z.boolean().optional(),
  status: z.enum(['ACTIVE', 'INACTIVE']).optional(),
});
