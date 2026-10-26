import * as z from 'zod';

const lineSchema = z.object({
  product_id: z.string().min(1, 'Product required'),
  uom_id: z.string().min(1, 'UOM required'),
  location_id: z.string().min(1, 'Location required'),
  ordered_qty: z.coerce.number().min(0.0001, 'Quantity required'),
  batch_number: z.string().optional(),
  notes: z.string().optional(),
});

export const dispatchOrderSchema = z.object({
  order_type: z.enum(['CUSTOMER_SALE', 'BRANCH_TRANSFER', 'VENDOR_RETURN', 'JOB_WORK_ISSUE']),
  customer_id: z.string().optional(),
  vendor_id: z.string().optional(),
  warehouse_id: z.string().min(1, 'Warehouse required'),
  dispatch_date: z.string().min(1, 'Dispatch date required'),
  carrier_type: z.enum(['SELF', 'CUSTOMER_PICKUP', 'TRANSPORTER', 'COURIER']),
  transporter_name: z.string().optional(),
  vehicle_number: z.string().optional(),
  driver_name: z.string().optional(),
  driver_phone: z.string().optional(),
  lr_number: z.string().optional(),
  notes: z.string().optional(),
  lines: z.array(lineSchema).min(1, 'At least one line required'),
});
