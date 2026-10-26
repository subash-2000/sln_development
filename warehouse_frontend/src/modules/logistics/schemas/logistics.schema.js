import * as z from 'zod';

const inwardLineSchema = z
  .object({
    product_id: z.string().min(1, 'Product required'),
    quantity: z.number().min(0.01, 'Quantity must be greater than 0'),
    uom_id: z.string().min(1, 'UOM required'),
    lot_number: z.string().optional(),
    unit_rate: z.number().min(0).optional(),
    gst_percent: z.number().min(0).max(100).optional(),
    hsn_code: z.string().optional(),
    part_number: z.string().optional(),
    package_count: z.number().min(0).optional(),
    box_count: z.number().min(0).optional(),
    box_quantity: z.number().min(0).optional(),
    has_remark: z.enum(['yes', 'no']).default('no'),
    expiry_date: z.string().optional(),
    remarks: z.string().optional(),
  })
  .superRefine((line, ctx) => {
    if (line.has_remark === 'yes' && !line.remarks?.trim()) {
      ctx.addIssue({
        code: 'custom',
        message: 'Enter remark text (Yes selected)',
        path: ['remarks'],
      });
    }
  });

export const logisticsInwardSchema = z.object({
  warehouse_id: z.string().min(1, 'Warehouse required'),
  vendor_id: z.string().optional(),
  reference_document_type: z.string().min(1, 'Doc type required'),
  reference_document_number: z.string().min(1, 'Doc number required'),
  transaction_date: z.string().min(1, 'Date required'),
  remarks: z.string().optional(),
  transporter_name: z.string().optional(),
  vehicle_number: z.string().optional(),
  lr_number: z.string().optional(),
  default_gst_percent: z.number().min(0).max(100).optional(),
  package_lines: z
    .array(
      z.object({
        part_number: z.string(),
        package_count: z.number(),
      })
    )
    .optional(),
  total_packages: z.number().optional(),
  items: z.array(inwardLineSchema).min(1, 'At least one item required'),
});
