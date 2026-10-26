import * as z from 'zod';

/**
 * User Validation Schema
 */
export const createUserSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').max(50),
  email: z.string().email('Invalid email address'),
  name: z.string().min(2, 'Full name must be at least 2 characters'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(6, 'Password must be at least 6 characters'),
  role_id: z.string().min(1, 'Please select a role'),
  company_ids: z.array(z.string()).min(1, 'Please select at least one company'),
  is_active: z.boolean().default(true),
});

export const editUserSchema = createUserSchema.extend({
  password: z.string().min(6, 'Password must be at least 6 characters').optional().or(z.literal('')),
});

export const userSchema = createUserSchema;
