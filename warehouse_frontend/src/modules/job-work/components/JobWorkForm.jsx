import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { jobWorkOrderSchema } from '../schemas/job-work.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { Plus, Trash2 } from 'lucide-react';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useProducts, useUOMs } from '../../products/hooks/use-products';

const JobWorkForm = ({ onSubmit, isLoading, defaultValues }) => {
  const { data: vendorsData } = useVendors({ page_size: 100 });
  const { data: warehousesData } = useWarehouses({ page_size: 100 });
  const { data: productsData } = useProducts({ page_size: 200 });
  const { data: uomsData } = useUOMs();

  const vendors = React.useMemo(() => {
    return (vendorsData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [vendorsData]);

  const warehouses = React.useMemo(() => {
    return (warehousesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [warehousesData]);

  const products = React.useMemo(() => {
    return (productsData?.items || []).slice().sort((a, b) =>
      (a.name || a.sku || '').localeCompare(b.name || b.sku || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [productsData]);

  const uoms = React.useMemo(() => {
    const list = Array.isArray(uomsData) ? uomsData : (uomsData?.items || []);
    return list.slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [uomsData]);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(jobWorkOrderSchema),
    defaultValues: defaultValues || {
      vendor_id: '',
      warehouse_id: '',
      order_type: 'PROCESSING',
      issue_date: new Date().toISOString().split('T')[0],
      expected_completion_date: '',
      bom_reference: '',
      notes: '',
      lines: [{ product_id: '', uom_id: '', ordered_qty: 1, notes: '' }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'lines' });

  const submit = (values) => {
    const payload = {
      ...values,
      expected_completion_date: values.expected_completion_date || null,
      bom_reference: values.bom_reference || null,
      notes: values.notes || null,
      lines: values.lines.map((line) => ({
        product_id: line.product_id,
        uom_id: line.uom_id,
        ordered_qty: line.ordered_qty,
        notes: line.notes || null,
      })),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <Card>
        <Card.Header>
          <h3 className="text-lg font-medium">Order details</h3>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Supplier (jobber)</label>
            <select
              {...register('vendor_id')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
            >
              <option value="">Select supplier</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
            {errors.vendor_id && <p className="text-xs text-red-500">{errors.vendor_id.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Warehouse</label>
            <select
              {...register('warehouse_id')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
            >
              <option value="">Select warehouse</option>
              {warehouses.map((wh) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </select>
            {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Order type</label>
            <select
              {...register('order_type')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
            >
              <option value="PROCESSING">Processing</option>
              <option value="CONVERSION">Conversion</option>
              <option value="ASSEMBLY">Assembly</option>
              <option value="FABRICATION">Fabrication</option>
              <option value="REPAIR">Repair</option>
            </select>
          </div>

          <Input label="Issue date" type="date" isRequired error={errors.issue_date?.message} {...register('issue_date')} />
          <Input label="Expected completion" type="date" error={errors.expected_completion_date?.message} {...register('expected_completion_date')} />
          <Input label="BOM reference" error={errors.bom_reference?.message} {...register('bom_reference')} />
          <div className="md:col-span-3">
            <Input label="Notes" error={errors.notes?.message} {...register('notes')} />
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Product lines</h3>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<Plus size={16} />}
            onClick={() => append({ product_id: '', uom_id: '', ordered_qty: 1, notes: '' })}
          >
            Add line
          </Button>
        </Card.Header>
        <Card.Body className="space-y-4">
          {fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end border-b border-gray-100 pb-4">
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Product</label>
                <select
                  {...register(`lines.${index}.product_id`)}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
                >
                  <option value="">Select product</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2 space-y-1.5">
                <label className="text-sm font-medium text-gray-700">UOM</label>
                <select
                  {...register(`lines.${index}.uom_id`)}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none"
                >
                  <option value="">UOM</option>
                  {uoms.map((u) => (
                    <option key={u.id} value={u.id}>{u.code}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <Input label="Qty" type="number" step="0.0001" {...register(`lines.${index}.ordered_qty`, { valueAsNumber: true })} />
              </div>
              <div className="md:col-span-3">
                <Input label="Line notes" {...register(`lines.${index}.notes`)} />
              </div>
              <div className="md:col-span-1 flex justify-end">
                {fields.length > 1 && (
                  <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)} aria-label="Remove line">
                    <Trash2 size={18} className="text-red-500" />
                  </Button>
                )}
              </div>
            </div>
          ))}
          {errors.lines?.message && <p className="text-xs text-red-500">{errors.lines.message}</p>}
        </Card.Body>
        <Card.Footer className="flex justify-end gap-3">
          <Button type="submit" isLoading={isLoading}>Save job work order</Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default JobWorkForm;
