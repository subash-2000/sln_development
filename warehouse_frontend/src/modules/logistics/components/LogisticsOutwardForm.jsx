import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { dispatchOrderSchema } from '../schemas/outward.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { Plus, Trash2 } from 'lucide-react';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useProducts, useUOMs } from '../../products/hooks/use-products';
import { useLocations } from '../../locations/hooks/use-locations';

const LogisticsOutwardForm = ({ onSubmit, isLoading }) => {
  const { data: warehousesData } = useWarehouses({ page_size: 100 });
  const { data: customersData } = useCustomers({ page_size: 100 });
  const { data: vendorsData } = useVendors({ page_size: 100 });
  const { data: productsData } = useProducts({ page_size: 200 });
  const { data: uomsData } = useUOMs();

  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(dispatchOrderSchema),
    defaultValues: {
      order_type: 'CUSTOMER_SALE',
      warehouse_id: '',
      dispatch_date: new Date().toISOString().split('T')[0],
      carrier_type: 'TRANSPORTER',
      lines: [{ product_id: '', uom_id: '', location_id: '', ordered_qty: 1 }],
    },
  });

  const warehouseId = watch('warehouse_id');
  const { data: locationsData } = useLocations(
    warehouseId ? { warehouse_id: warehouseId, page_size: 200 } : { page_size: 0 }
  );

  const { fields, append, remove } = useFieldArray({ control, name: 'lines' });

  const submit = (values) => {
    onSubmit({
      ...values,
      customer_id: values.customer_id || null,
      vendor_id: values.vendor_id || null,
      transporter_name: values.transporter_name || null,
      vehicle_number: values.vehicle_number || null,
      driver_name: values.driver_name || null,
      driver_phone: values.driver_phone || null,
      lr_number: values.lr_number || null,
      notes: values.notes || null,
      lines: values.lines.map((line) => ({
        product_id: line.product_id,
        uom_id: line.uom_id,
        location_id: line.location_id,
        ordered_qty: line.ordered_qty,
        batch_number: line.batch_number || null,
        notes: line.notes || null,
      })),
    });
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <Card>
        <Card.Header><h3 className="text-lg font-medium">Dispatch header</h3></Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Order type</label>
            <select {...register('order_type')} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="CUSTOMER_SALE">Customer sale</option>
              <option value="BRANCH_TRANSFER">Branch transfer</option>
              <option value="VENDOR_RETURN">Supplier return</option>
              <option value="JOB_WORK_ISSUE">Job work issue</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Warehouse</label>
            <select {...register('warehouse_id')} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="">Select warehouse</option>
              {warehousesData?.items?.map((wh) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </select>
            {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
          </div>
          <Input label="Dispatch date" type="date" isRequired {...register('dispatch_date')} />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Customer</label>
            <select {...register('customer_id')} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="">Optional</option>
              {customersData?.items?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Supplier</label>
            <select {...register('vendor_id')} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="">Optional</option>
              {vendorsData?.items?.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Carrier</label>
            <select {...register('carrier_type')} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="TRANSPORTER">Transporter</option>
              <option value="SELF">Self</option>
              <option value="CUSTOMER_PICKUP">Customer pickup</option>
              <option value="COURIER">Courier</option>
            </select>
          </div>
          <Input label="Transporter" {...register('transporter_name')} />
          <Input label="Vehicle number" {...register('vehicle_number')} />
          <Input label="LR number" {...register('lr_number')} />
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Lines</h3>
          <Button type="button" variant="secondary" size="sm" leftIcon={<Plus size={16} />} onClick={() => append({ product_id: '', uom_id: '', location_id: '', ordered_qty: 1 })}>
            Add line
          </Button>
        </Card.Header>
        <Card.Body className="space-y-4">
          {fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end border-b pb-4">
              <div className="md:col-span-3">
                <select {...register(`lines.${index}.product_id`)} className="w-full border rounded-lg px-3 py-2 text-sm">
                  <option value="">Product</option>
                  {productsData?.items?.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <select {...register(`lines.${index}.uom_id`)} className="w-full border rounded-lg px-3 py-2 text-sm">
                  <option value="">UOM</option>
                  {uomsData?.map((u) => (
                    <option key={u.id} value={u.id}>{u.code}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-3">
                <select {...register(`lines.${index}.location_id`)} className="w-full border rounded-lg px-3 py-2 text-sm" disabled={!warehouseId}>
                  <option value="">Location</option>
                  {locationsData?.items?.map((loc) => (
                    <option key={loc.id} value={loc.id}>{loc.code} — {loc.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <Input type="number" step="0.0001" label="Qty" {...register(`lines.${index}.ordered_qty`, { valueAsNumber: true })} />
              </div>
              <div className="md:col-span-2 flex justify-end">
                {fields.length > 1 && (
                  <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)}>
                    <Trash2 className="text-red-500" size={18} />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </Card.Body>
        <Card.Footer className="flex justify-end">
          <Button type="submit" isLoading={isLoading}>Create outward dispatch</Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default LogisticsOutwardForm;
