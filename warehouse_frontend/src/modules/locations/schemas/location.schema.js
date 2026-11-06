import * as z from 'zod';

export const locationSchema = z.object({
  warehouse_id: z.string().min(1, 'Warehouse required'),
  code: z.string().min(2, 'Code required').max(50),
  name: z.string().min(2, 'Name required').max(200),
  // Backend uses INTERNAL, RECEIVING, DISPATCH, etc. (legacy UI values still accepted on create)
  location_type: z.string().min(1, 'Location type required'),
  zone: z.string().optional(),
  aisle: z.string().optional(),
  shelf: z.string().optional(),
  bin: z.string().optional(),
  is_active: z.coerce.boolean().default(true),
});
