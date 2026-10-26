import * as z from 'zod';

export const locationSchema = z.object({
  warehouse_id: z.string().min(1, 'Warehouse required'),
  code: z.string().min(2, 'Code required').max(50),
  name: z.string().min(2, 'Name required').max(200),
  location_type: z.enum(['STORAGE', 'RECEIVING', 'SHIPPING', 'PICKING', 'VIRTUAL']),
  zone: z.string().optional(),
  aisle: z.string().optional(),
  shelf: z.string().optional(),
  bin: z.string().optional(),
  is_active: z.boolean().default(true),
});
