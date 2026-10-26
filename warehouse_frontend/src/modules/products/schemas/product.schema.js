import * as z from 'zod';

export const productSchema = z.object({
  sku: z.string().min(2, 'SKU must be at least 2 characters').max(100),
  name: z.string().min(2, 'Name must be at least 2 characters').max(200),
  part_number: z.string().max(100).optional().nullable(),
  description: z.string().optional().nullable(),
  category_id: z.string().optional().nullable(),
  uom_id: z.string().min(1, 'UOM is required'),
  hsn_code: z.string().optional().nullable(),
  net_weight: z.preprocess(
    (v) => (v === '' || v === null || v === undefined ? null : Number(v)),
    z.number().nonnegative().nullable().optional()
  ),
  company_id: z.string().optional(),
  batch_number: z.string().max(100).optional().nullable(),
  heat_number: z.string().max(100).optional().nullable(),
  gauge_number: z.string().max(100).optional().nullable(),
  mill_name: z.string().max(255).optional().nullable(),
  package_tracking_type: z.string().optional().nullable(),
  package_tracking_value: z.string().max(255).optional().nullable(),
  packing_ratio: z.string().max(50).optional().nullable(),
  is_lot_tracked: z.boolean().default(false),
  is_active: z.boolean().default(true),
  vendor_ids: z.preprocess(
    (value) => {
      if (value == null || value === '') return [];
      return Array.isArray(value) ? value.filter(Boolean) : [value];
    },
    z.array(z.string()).min(1, 'Select at least one supplier for this type')
  ),
}).superRefine((data, ctx) => {
  if (data.package_tracking_type && !data.package_tracking_value?.trim()) {
    ctx.addIssue({
      code: 'custom',
      message: 'Enter pallet or cotton box number',
      path: ['package_tracking_value'],
    });
  }
});
