import * as z from 'zod';

const lineSchema = z.object({
  product_id: z.string().min(1, 'Product is required'),
  uom_id: z.string().min(1, 'UOM is required'),
  ordered_qty: z.coerce.number().min(0.0001, 'Quantity must be greater than 0'),
  notes: z.string().optional(),
});

export const jobWorkOrderSchema = z.object({
  vendor_id: z.string().min(1, 'Supplier is required'),
  warehouse_id: z.string().min(1, 'Warehouse is required'),
  order_type: z.enum(['PROCESSING', 'CONVERSION', 'ASSEMBLY', 'FABRICATION', 'REPAIR']),
  issue_date: z.string().min(1, 'Issue date is required'),
  expected_completion_date: z.string().optional(),
  bom_reference: z.string().optional(),
  notes: z.string().optional(),
  lines: z.array(lineSchema).min(1, 'At least one product line is required'),
});
