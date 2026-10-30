import React, { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Trash2 } from 'lucide-react';
import { returnOrderSchema } from '../schemas/return.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useProducts, useUOMs } from '../../products/hooks/use-products';

const selectClass =
  'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500';

const ReturnForm = ({ onSubmit, isLoading, defaultValues }) => {
  const { data: warehousesData } = useWarehouses({ page_size: 100 });
  const { data: customersData } = useCustomers({ page_size: 200 });
  const { data: vendorsData } = useVendors({ page_size: 200 });
  const { data: productsData } = useProducts({ page_size: 500 });
  const { data: uomsData } = useUOMs();

  const warehouses = React.useMemo(() => {
    return (warehousesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [warehousesData]);

  const customers = React.useMemo(() => {
    return (customersData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [customersData]);

  const vendors = React.useMemo(() => {
    return (vendorsData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [vendorsData]);

  const products = React.useMemo(() => {
    return (productsData?.items || []).slice().sort((a, b) =>
      (a.sku || a.name || '').localeCompare(b.sku || b.name || '', undefined, { numeric: true, sensitivity: 'base' })
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
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(returnOrderSchema),
    defaultValues: defaultValues || {
      return_type: 'VENDOR_RETURN',
      warehouse_id: '',
      customer_id: '',
      vendor_id: '',
      return_date: new Date().toISOString().split('T')[0],
      reason: '',
      notes: '',
      lines: [{ product_id: '', uom_id: '', quantity_returned: 1, lot_number: '', notes: '' }],
    },
  });

  const returnType = watch('return_type');
  const { fields, append, remove } = useFieldArray({ control, name: 'lines' });

  useEffect(() => {
    const products = productsData?.items || [];
    const uoms = uomsData?.items || uomsData || [];
    const defaultUom = Array.isArray(uoms) ? uoms[0]?.id : uoms?.[0]?.id;
    fields.forEach((field, index) => {
      const line = watch(`lines.${index}`);
      if (line?.product_id && !line?.uom_id) {
        const product = products.find((p) => p.id === line.product_id);
        if (product?.uom_id) {
          setValue(`lines.${index}.uom_id`, product.uom_id);
        } else if (defaultUom) {
          setValue(`lines.${index}.uom_id`, defaultUom);
        }
      }
    });
  }, [productsData, uomsData, fields, watch, setValue]);

  const submit = (values) => {
    onSubmit({
      warehouse_id: values.warehouse_id,
      return_type: values.return_type,
      customer_id: values.return_type === 'CUSTOMER_RETURN' ? values.customer_id : null,
      vendor_id: values.return_type === 'VENDOR_RETURN' ? values.vendor_id : null,
      return_date: values.return_date,
      reason: values.reason || null,
      notes: values.notes || null,
      lines: values.lines.map((line) => ({
        product_id: line.product_id,
        uom_id: line.uom_id,
        quantity_returned: line.quantity_returned,
        lot_number: line.lot_number || null,
        notes: line.notes || null,
      })),
    });
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <Card>
        <Card.Header>
          <h3 className="text-lg font-medium">Return header</h3>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Return type</label>
            <select {...register('return_type')} className={selectClass}>
              <option value="VENDOR_RETURN">Supplier return (RTV / rejection)</option>
              <option value="CUSTOMER_RETURN">Customer return (RMA)</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Warehouse</label>
            <select {...register('warehouse_id')} className={selectClass}>
              <option value="">Select warehouse</option>
              {warehouses.map((wh) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </select>
            {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
          </div>
          <Input label="Return date" type="date" isRequired {...register('return_date')} error={errors.return_date?.message} />
          {returnType === 'CUSTOMER_RETURN' && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Customer</label>
              <select {...register('customer_id')} className={selectClass}>
                <option value="">Select customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              {errors.customer_id && <p className="text-xs text-red-500">{errors.customer_id.message}</p>}
            </div>
          )}
          {returnType === 'VENDOR_RETURN' && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Supplier</label>
              <select {...register('vendor_id')} className={selectClass}>
                <option value="">Select supplier</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
              {errors.vendor_id && <p className="text-xs text-red-500">{errors.vendor_id.message}</p>}
            </div>
          )}
          <Input label="Reason" {...register('reason')} placeholder="e.g. Excel rejection challan" />
          <div className="md:col-span-2 space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Notes</label>
            <textarea
              {...register('notes')}
              rows={2}
              className={selectClass}
              placeholder="Challan, transporter, E-Sugam, etc."
            />
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="flex flex-row items-center justify-between">
          <h3 className="text-lg font-medium">Line items</h3>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<Plus size={16} />}
            onClick={() => append({ product_id: '', uom_id: '', quantity_returned: 1, lot_number: '', notes: '' })}
          >
            Add line
          </Button>
        </Card.Header>
        <Card.Body className="space-y-4">
          {fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end border-b border-gray-100 pb-4 last:border-0">
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Product</label>
                <select {...register(`lines.${index}.product_id`)} className={selectClass}>
                  <option value="">Select product</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2 space-y-1.5">
                <label className="text-sm font-medium text-gray-700">UOM</label>
                <select {...register(`lines.${index}.uom_id`)} className={selectClass}>
                  <option value="">UOM</option>
                  {uoms.map((u) => (
                    <option key={u.id} value={u.id}>{u.code || u.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <Input
                  label="Qty"
                  type="number"
                  step="any"
                  min="0"
                  {...register(`lines.${index}.quantity_returned`)}
                />
              </div>
              <div className="md:col-span-2">
                <Input label="Lot / batch" {...register(`lines.${index}.lot_number`)} />
              </div>
              <div className="md:col-span-1 flex justify-end">
                {fields.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)} aria-label="Remove line">
                    <Trash2 size={16} className="text-red-500" />
                  </Button>
                )}
              </div>
            </div>
          ))}
          {errors.lines?.message && <p className="text-xs text-red-500">{errors.lines.message}</p>}
        </Card.Body>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving…' : 'Create return order'}
        </Button>
      </div>
    </form>
  );
};

export default ReturnForm;
