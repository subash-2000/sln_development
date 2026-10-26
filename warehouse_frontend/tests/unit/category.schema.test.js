import { describe, it, expect } from 'vitest';
import { getCategorySchema, categorySchema } from '../../src/modules/products/categories/schemas/category.schema';

describe('Category Schema Validation', () => {
  const validBaseData = {
    code: 'ELEC',
    name: 'Electronics & Hardware',
    description: 'Consumer and industrial electronics',
    is_active: true,
  };

  it('should validate valid category data', () => {
    const schema = getCategorySchema();
    const result = schema.safeParse(validBaseData);
    expect(result.success).toBe(true);
  });

  it('should fail when code is too short', () => {
    const schema = getCategorySchema();
    const result = schema.safeParse({ ...validBaseData, code: 'E' });
    expect(result.success).toBe(false);
    expect(result.error.issues.some((i) => i.path.includes('code'))).toBe(true);
  });

  it('should fail when name is empty', () => {
    const schema = getCategorySchema();
    const result = schema.safeParse({ ...validBaseData, name: '' });
    expect(result.success).toBe(false);
    expect(result.error.issues.some((i) => i.path.includes('name'))).toBe(true);
  });

  it('should detect duplicate category code', () => {
    const existingCategories = [
      { id: 'cat-1', code: 'ELEC', name: 'Electronics' },
      { id: 'cat-2', code: 'GRAINS', name: 'Grains' },
    ];
    const schema = getCategorySchema(false, existingCategories);
    const result = schema.safeParse({ ...validBaseData, code: 'ELEC' });
    expect(result.success).toBe(false);
    const codeError = result.error.issues.find((i) => i.path.includes('code'));
    expect(codeError?.message).toContain("already exists with another category");
  });

  it('should allow duplicate check to pass for same category in edit mode', () => {
    const existingCategories = [
      { id: 'cat-1', code: 'ELEC', name: 'Electronics' },
      { id: 'cat-2', code: 'GRAINS', name: 'Grains' },
    ];
    const schema = getCategorySchema(true, existingCategories, 'cat-1');
    const result = schema.safeParse({ ...validBaseData, code: 'ELEC' });
    expect(result.success).toBe(true);
  });

  it('should prevent category from being its own parent in edit mode', () => {
    const schema = getCategorySchema(true, [], 'cat-1');
    const result = schema.safeParse({ ...validBaseData, parent_id: 'cat-1' });
    expect(result.success).toBe(false);
    const parentError = result.error.issues.find((i) => i.path.includes('parent_id'));
    expect(parentError?.message).toContain('cannot be its own parent');
  });
});
