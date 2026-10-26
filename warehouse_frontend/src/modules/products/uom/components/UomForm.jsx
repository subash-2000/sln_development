import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Button from '../../../../components/ui/Button';
import Input from '../../../../components/ui/Input';
import Card from '../../../../components/ui/Card';
import { useUomCategories } from '../hooks/use-uom-master';

const uomSchema = z.object({
  category_id: z.string().min(1, 'Category is required'),
  code: z.string().min(1, 'Code is required').max(20),
  name: z.string().min(1, 'Name is required').max(100),
  uom_type: z.enum(['REFERENCE', 'BIGGER', 'SMALLER']),
  factor: z.coerce.number().positive('Factor must be > 0'),
  rounding_precision: z.coerce.number().positive('Precision must be > 0'),
  status: z.enum(['ACTIVE', 'INACTIVE']).optional(),
});

const selectClass =
  'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500';

const UomForm = ({ onSubmit, isLoading, defaultValues, isEdit = false }) => {
  const { data: categories = [] } = useUomCategories();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(uomSchema),
    defaultValues: defaultValues || {
      category_id: '',
      code: '',
      name: '',
      uom_type: 'REFERENCE',
      factor: 1,
      rounding_precision: 0.001,
      status: 'ACTIVE',
    },
  });

  const submit = (values) => {
    const payload = {
      category_id: values.category_id,
      name: values.name,
      uom_type: values.uom_type,
      factor: values.factor,
      rounding_precision: values.rounding_precision,
      status: values.status || 'ACTIVE',
    };
    if (!isEdit) {
      payload.code = values.code;
    }
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <Card>
        <Card.Header>
          <h3 className="text-lg font-medium">Unit of measure</h3>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Category</label>
            <select {...register('category_id')} className={selectClass}>
              <option value="">Select category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {errors.category_id && <p className="text-xs text-red-500">{errors.category_id.message}</p>}
          </div>
          <Input
            label="Code"
            isRequired
            disabled={isEdit}
            {...register('code')}
            error={errors.code?.message}
            placeholder="e.g. UNT, KG"
          />
          <Input label="Name" isRequired {...register('name')} error={errors.name?.message} />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">UOM type</label>
            <select {...register('uom_type')} className={selectClass}>
              <option value="REFERENCE">Reference (base unit)</option>
              <option value="BIGGER">Bigger than reference</option>
              <option value="SMALLER">Smaller than reference</option>
            </select>
          </div>
          <Input
            label="Conversion factor"
            type="number"
            step="any"
            {...register('factor')}
            error={errors.factor?.message}
          />
          <Input
            label="Rounding precision"
            type="number"
            step="any"
            {...register('rounding_precision')}
            error={errors.rounding_precision?.message}
          />
          {isEdit && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Status</label>
              <select {...register('status')} className={selectClass}>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          )}
        </Card.Body>
      </Card>
      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving…' : isEdit ? 'Update UOM' : 'Create UOM'}
        </Button>
      </div>
    </form>
  );
};

export default UomForm;
