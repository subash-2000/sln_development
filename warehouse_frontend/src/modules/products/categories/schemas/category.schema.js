import * as z from 'zod';

export const categorySchema = z.object({
  code: z
    .string()
    .min(2, 'Category code must be at least 2 characters')
    .max(50, 'Category code cannot exceed 50 characters')
    .regex(/^[A-Za-z0-9_-]+$/, 'Code can only contain letters, numbers, hyphens, and underscores'),
  name: z
    .string()
    .min(2, 'Category name must be at least 2 characters')
    .max(255, 'Category name cannot exceed 255 characters'),
  company_id: z.string().optional().nullable(),
  parent_id: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
  is_active: z.boolean().default(true),
});

export const getCategorySchema = (isEdit = false, existingCategories = [], currentCategoryId = null) => {
  return categorySchema.superRefine((data, ctx) => {
    if (existingCategories && existingCategories.length > 0) {
      const trimmedCode = (data.code || '').trim().toUpperCase();

      const duplicateCode = existingCategories.find((cat) => {
        if (isEdit && currentCategoryId && String(cat.id) === String(currentCategoryId)) {
          return false;
        }
        return (cat.code || '').trim().toUpperCase() === trimmedCode;
      });

      if (duplicateCode) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['code'],
          message: `Category code '${data.code}' already exists with another category`,
        });
      }
    }

    if (isEdit && currentCategoryId && String(data.parent_id) === String(currentCategoryId)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['parent_id'],
        message: 'A category cannot be its own parent',
      });
    }
  });
};
