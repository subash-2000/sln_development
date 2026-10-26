import { z } from 'zod';

const returnLineSchema = z.object({
  product_id: z.string().min(1, 'Product is required'),
  uom_id: z.string().min(1, 'UOM is required'),
  quantity_returned: z.coerce.number().positive('Quantity must be greater than 0'),
  lot_number: z.string().optional(),
  notes: z.string().optional(),
});

export const returnOrderSchema = z
  .object({
    warehouse_id: z.string().min(1, 'Warehouse is required'),
    return_type: z.enum(['CUSTOMER_RETURN', 'VENDOR_RETURN']),
    customer_id: z.string().optional(),
    vendor_id: z.string().optional(),
    return_date: z.string().min(1, 'Return date is required'),
    reason: z.string().optional(),
    notes: z.string().optional(),
    lines: z.array(returnLineSchema).min(1, 'At least one line is required'),
  })
  .superRefine((data, ctx) => {
    if (data.return_type === 'CUSTOMER_RETURN' && !data.customer_id) {
      ctx.addIssue({ code: 'custom', message: 'Customer is required', path: ['customer_id'] });
    }
    if (data.return_type === 'VENDOR_RETURN' && !data.vendor_id) {
      ctx.addIssue({ code: 'custom', message: 'Supplier is required', path: ['vendor_id'] });
    }
  });
