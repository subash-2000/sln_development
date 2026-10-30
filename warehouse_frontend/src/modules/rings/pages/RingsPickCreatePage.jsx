import React, { useMemo, useState } from 'react';
import { Plus, Trash2, Search } from 'lucide-react';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import Input from '../../../components/ui/Input';
import SearchableSelect from '../../../components/ui/SearchableSelect';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useCreateRingsPick, useRingsStock } from '../hooks/use-rings';

const selectTriggerClass = 'max-w-none h-9 px-2 rounded-md';
const noSpinnerClass =
  'w-full min-w-0 bg-white border border-gray-200 rounded-md px-1.5 py-1.5 text-sm tabular-nums focus:ring-2 focus:ring-primary-500 outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none';
const thBase =
  'px-2 py-2 text-[10px] font-semibold text-gray-400 uppercase leading-tight text-left whitespace-nowrap align-middle';
const tdBase = 'px-2 py-2 align-middle';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const emptyLine = () => ({
  vendor_id: '',
  vendor_name: '',
  product_id: '',
  lot_id: '',
  invoice_number: '',
  invoice_date: '',
  transporter_name: '',
  received_date: '',
  pallet_count: '',
  qty_per_pallet: '',
  quantity: '',
  heat_number: '',
  per_ring_weight: '',
  packing_weight: '',
  unit_rate: '',
});

const dash = (value) => {
  if (value === null || value === undefined) return '—';
  const text = String(value).trim();
  return text ? text : '—';
};

const formatShortDate = (value) => {
  if (!value) return '—';
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dash(value);
  return `${String(d.getDate()).padStart(2, '0')}-${MONTHS[d.getMonth()]}-${String(d.getFullYear()).slice(-2)}`;
};

const formatQty = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v)) return '—';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(v);
};

const formatWt = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v)) return '—';
  return v.toFixed(3);
};

const grossWeight = (qty, ringWt) => (Number(qty) || 0) * (Number(ringWt) || 0);

const totalWeight = (qty, ringWt, packingWt) => grossWeight(qty, ringWt) + (Number(packingWt) || 0);

const compactQty = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v) || v === 0) return '0';
  if (Number.isInteger(v)) return String(v);
  return String(v);
};

const productLabel = (row) => {
  const sku = String(row?.sku || row?.product_sku || '').trim();
  const name = String(row?.name || row?.product_name || '').trim();
  if (!name || !sku || name.toUpperCase() === sku.toUpperCase()) return sku || name || 'Product';
  return sku;
};

const lotId = (row) =>
  `${row?.vendor_id || ''}::${row?.product_id || ''}::${row?.heat_number || ''}::${row?.dc_number || row?.invoice_number || ''}`;

const RingsPickCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync, isPending } = useCreateRingsPick();
  const { data: warehousesData } = useWarehouses();
  const { data: vendorsData } = useVendors({ page_size: 200 });
  const { data: customersData } = useCustomers({ page_size: 200, is_buyer: true, status: 'ACTIVE' });
  const { register, control, handleSubmit, watch, setValue, getValues } = useForm({
    defaultValues: {
      warehouse_id: '',
      vendor_id: '',
      workflow: 'JOB_WORK',
      customer_id: '',
      po_number: '',
      lines: [emptyLine()],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: 'lines' });
  const vendorId = watch('vendor_id');
  const warehouseId = watch('warehouse_id');
  const customerId = watch('customer_id');
  const workflow = watch('workflow');
  const poNumber = watch('po_number');
  const watchedLines = useWatch({ control, name: 'lines' }) || [];

  const [stockSupplierFilter, setStockSupplierFilter] = useState('ALL');
  const [stockSearch, setStockSearch] = useState('');

  // Fetch stock across all suppliers for the selected warehouse
  const { data: stock, isLoading: isStockLoading } = useRingsStock({ warehouse_id: warehouseId });
  const stockRows = useMemo(() => {
    const rows = (Array.isArray(stock) ? [...stock] : []).filter(
      (row) => Number(row.quantity_available || 0) > 0
    );
    rows.sort((a, b) => {
      const qtyDiff = Number(b.quantity_available || 0) - Number(a.quantity_available || 0);
      if (qtyDiff !== 0) return qtyDiff;
      return String(a.product_sku || '').localeCompare(String(b.product_sku || ''));
    });
    return rows;
  }, [stock]);

  const warehouses = useMemo(() => {
    return (warehousesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [warehousesData]);
  const vendors = useMemo(() => {
    return (vendorsData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [vendorsData]);
  const buyers = useMemo(() => {
    return (customersData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [customersData]);
  const vendor = vendors.find((v) => String(v.id) === String(vendorId));
  const buyer = buyers.find((c) => String(c.id) === String(customerId));
  const workflowOptions = [
    { id: 'JOB_WORK', name: 'Job Work' },
    { id: 'DIRECT_INVOICE', name: 'Direct Invoice' },
  ];

  // List of suppliers that actually have stock available
  const vendorsWithStock = useMemo(() => {
    const counts = {};
    for (const r of stockRows) {
      if (!r.vendor_id) continue;
      counts[r.vendor_id] = (counts[r.vendor_id] || 0) + 1;
    }
    return vendors
      .filter((v) => counts[v.id])
      .map((v) => ({ id: String(v.id), name: v.name, count: counts[v.id] }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [stockRows, vendors]);

  // Stock rows displayed in the Available table (filtered by table's supplier filter + search)
  const displayedStockRows = useMemo(() => {
    return stockRows.filter((row) => {
      if (stockSupplierFilter !== 'ALL' && String(row.vendor_id) !== String(stockSupplierFilter)) {
        return false;
      }
      if (stockSearch.trim()) {
        const query = stockSearch.toLowerCase().trim();
        const sku = String(row.product_sku || '').toLowerCase();
        const name = String(row.product_name || '').toLowerCase();
        const heat = String(row.heat_number || '').toLowerCase();
        const dc = String(row.dc_number || '').toLowerCase();
        const vendorName = String(row.vendor_name || '').toLowerCase();
        if (!sku.includes(query) && !name.includes(query) && !heat.includes(query) && !dc.includes(query) && !vendorName.includes(query)) {
          return false;
        }
      }
      return true;
    });
  }, [stockRows, stockSupplierFilter, stockSearch]);

  const allProductOptions = useMemo(() => {
    const seen = new Set();
    return stockRows.flatMap((row) => {
      const id = String(row.product_id);
      if (seen.has(id)) return [];
      seen.add(id);
      return [{ id: row.product_id, sku: row.product_sku, name: row.product_name, vendor_id: row.vendor_id }];
    });
  }, [stockRows]);

  const getProductOptionsForLine = (line) => {
    const lineVendorId = line?.vendor_id || vendorId;
    if (!lineVendorId) return allProductOptions;
    const seen = new Set();
    return stockRows
      .filter((row) => String(row.vendor_id) === String(lineVendorId))
      .flatMap((row) => {
        const id = String(row.product_id);
        if (seen.has(id)) return [];
        seen.add(id);
        return [{ id: row.product_id, sku: row.product_sku, name: row.product_name }];
      });
  };

  const remainingForLot = (lot, exceptIndex) => {
    const available = Number(lot?.quantity_available || 0);
    const key = lotId({ ...lot, invoice_number: lot.dc_number || lot.invoice_number });
    const used = (watchedLines || []).reduce((sum, line, i) => {
      if (i === exceptIndex) return sum;
      if (lotId(line) !== key) return sum;
      return sum + Number(line.quantity || 0);
    }, 0);
    return Math.max(0, available - used);
  };

  const invoicesForProduct = (productId, exceptIndex, lineVendorId) => {
    if (!productId) return [];
    const targetVendor = lineVendorId || vendorId;
    const pool = targetVendor
      ? stockRows.filter((row) => String(row.vendor_id) === String(targetVendor))
      : stockRows;
    return pool
      .filter((row) => String(row.product_id) === String(productId))
      .map((row) => ({ ...row, remaining: remainingForLot(row, exceptIndex) }))
      .filter((row) => row.remaining > 0 || lotId({ ...row, invoice_number: row.dc_number }) === watchedLines[exceptIndex]?.lot_id);
  };

  const applyLot = (index, lot, remaining) => {
    const qty = remaining > 0 ? remaining : Number(lot.quantity_available || 0);
    const packing = Number(lot.packing_weight || 0);
    const lotAvail = Number(lot.quantity_available || 0);
    const linePacking = lotAvail > 0 ? packing * (qty / lotAvail) : packing;
    setValue(`lines.${index}.vendor_id`, lot.vendor_id || '', { shouldDirty: true });
    setValue(`lines.${index}.vendor_name`, lot.vendor_name || '', { shouldDirty: true });
    setValue(`lines.${index}.lot_id`, lotId({ ...lot, invoice_number: lot.dc_number }), { shouldDirty: true });
    setValue(`lines.${index}.product_id`, lot.product_id, { shouldDirty: true, shouldValidate: true });
    setValue(`lines.${index}.invoice_number`, lot.dc_number || '', { shouldDirty: true });
    setValue(`lines.${index}.invoice_date`, lot.dc_date || '', { shouldDirty: true });
    setValue(`lines.${index}.transporter_name`, lot.transporter_name || '', { shouldDirty: true });
    setValue(`lines.${index}.received_date`, lot.received_date || '', { shouldDirty: true });
    setValue(`lines.${index}.heat_number`, lot.heat_number || '', { shouldDirty: true });
    setValue(`lines.${index}.per_ring_weight`, lot.per_ring_weight ?? '', { shouldDirty: true });
    setValue(`lines.${index}.unit_rate`, lot.unit_rate ?? '', { shouldDirty: true });
    setValue(`lines.${index}.packing_weight`, Number.isFinite(linePacking) ? linePacking.toFixed(3) : '0', { shouldDirty: true });
    setValue(`lines.${index}.quantity`, compactQty(qty), { shouldDirty: true });
  };

  const onProductChange = (index, productId) => {
    const line = getValues(`lines.${index}`);
    setValue(`lines.${index}.product_id`, productId, { shouldDirty: true, shouldValidate: true });
    setValue(`lines.${index}.lot_id`, '', { shouldDirty: true });
    setValue(`lines.${index}.invoice_number`, '', { shouldDirty: true });
    setValue(`lines.${index}.invoice_date`, '', { shouldDirty: true });
    setValue(`lines.${index}.transporter_name`, '', { shouldDirty: true });
    setValue(`lines.${index}.received_date`, '', { shouldDirty: true });
    setValue(`lines.${index}.heat_number`, '', { shouldDirty: true });
    setValue(`lines.${index}.per_ring_weight`, '', { shouldDirty: true });
    setValue(`lines.${index}.packing_weight`, '', { shouldDirty: true });
    setValue(`lines.${index}.quantity`, '', { shouldDirty: true });
    setValue(`lines.${index}.unit_rate`, '', { shouldDirty: true });
    const invoices = invoicesForProduct(productId, index, line?.vendor_id);
    if (invoices.length === 1) {
      applyLot(index, invoices[0], invoices[0].remaining);
    }
  };

  const onInvoiceChange = (index, value) => {
    const line = getValues(`lines.${index}`);
    const productId = line?.product_id;
    const lineVendorId = line?.vendor_id;
    const lot = invoicesForProduct(productId, index, lineVendorId).find(
      (row) => lotId({ ...row, invoice_number: row.dc_number }) === value
    );
    if (!lot) return;
    applyLot(index, lot, lot.remaining);
  };

  const lotForLine = (line) => {
    if (!line) return null;
    if (line.lot_id) {
      const match = stockRows.find(
        (row) => lotId({ ...row, invoice_number: row.dc_number }) === line.lot_id
      );
      if (match) return match;
    }
    return stockRows.find(
      (row) =>
        String(row.product_id) === String(line.product_id) &&
        String(row.heat_number || '') === String(line.heat_number || '') &&
        (!line.vendor_id || String(row.vendor_id) === String(line.vendor_id))
    );
  };

  const lineLimit = (index, line) => {
    const lot = lotForLine(line);
    if (!lot) return null;
    return remainingForLot(lot, index);
  };

  const handleSupplierChange = (newVendorId) => {
    setValue('vendor_id', newVendorId, { shouldDirty: true });
    if (newVendorId) {
      setStockSupplierFilter(newVendorId);
    }
  };

  const handleQuickPick = (lot) => {
    const targetVendorId = String(lot.vendor_id);

    // If no top supplier is selected yet, default to this vendor
    if (!getValues('vendor_id')) {
      setValue('vendor_id', targetVendorId, { shouldDirty: true });
    }

    const currentLines = getValues('lines') || [];
    const emptyIndex = currentLines.findIndex((l) => !l.product_id && !l.heat_number);
    const targetIndex = emptyIndex !== -1 ? emptyIndex : currentLines.length;
    const remaining = remainingForLot(lot, targetIndex);

    if (emptyIndex !== -1) {
      applyLot(emptyIndex, lot, remaining);
    } else {
      append(emptyLine());
      setTimeout(() => {
        applyLot(targetIndex, lot, remaining);
      }, 0);
    }
  };

  const lineQtyError = (index, line) => {
    const max = lineLimit(index, line);
    if (max == null) return '';
    const pallets = Number(line?.pallet_count);
    const per = Number(line?.qty_per_pallet);
    const qty = Number(line?.quantity);
    const limitLabel = formatQty(max);

    if (
      Number.isFinite(pallets) && pallets > 0
      && Number.isFinite(per) && per > 0
      && pallets * per > max + 0.0001
    ) {
      return `${compactQty(pallets)} × ${compactQty(per)} = ${formatQty(pallets * per)} exceeds available ${limitLabel}`;
    }
    if (Number.isFinite(qty) && qty > max + 0.0001) {
      return `Quantity ${compactQty(qty)} exceeds available ${limitLabel}`;
    }
    return '';
  };

  const onPalletChange = (index) => {
    queueMicrotask(() => {
      const line = getValues(`lines.${index}`);
      const pallets = Number(line?.pallet_count || 0);
      const per = Number(line?.qty_per_pallet || 0);
      if (!(pallets > 0 && per > 0)) return;
      const max = lineLimit(index, line);
      const packed = pallets * per;
      if (max != null && packed > max) return;
      setValue(`lines.${index}.quantity`, compactQty(packed), { shouldDirty: true });
    });
  };

  const onInvalid = (errors) => {
    console.error('Validation errors:', errors);
    if (errors.warehouse_id) {
      window.alert('Please select a warehouse.');
      return;
    }
    window.alert('Please check the required fields before saving.');
  };

  const onSubmit = async (form) => {
    try {
      if (!form.warehouse_id) {
        window.alert('Please select a warehouse.');
        return;
      }
      const filled = form.lines.filter((line) => line.product_id && Number(line.quantity || 0) > 0);
      if (!filled.length) {
        window.alert('Add at least one product with quantity.');
        return;
      }
      const overIndex = form.lines.findIndex((line, index) => lineQtyError(index, line));
      if (overIndex !== -1) {
        window.alert(`Line ${overIndex + 1}: ${lineQtyError(overIndex, form.lines[overIndex])}`);
        return;
      }
      for (const [index, line] of filled.entries()) {
        const lot = lotForLine(line);
        if (lot) {
          const max = remainingForLot(lot, form.lines.indexOf(line));
          if (Number(line.quantity) > max + 0.0001) {
            window.alert(`Line ${index + 1}: quantity ${line.quantity} is more than remaining ${compactQty(max)}`);
            return;
          }
        }
      }

      for (const line of filled) {
        const vId = line.vendor_id || form.vendor_id;
        if (!vId) {
          window.alert('Please select a supplier for each pick line.');
          return;
        }
      }

      const first = filled[0];
      const primaryVendorId = form.vendor_id || first.vendor_id;
      const totalPacking = filled.reduce((sum, line) => sum + Number(line.packing_weight || 0), 0);

      const vVendor = vendors.find((v) => String(v.id) === String(primaryVendorId));
      let workflow = form.workflow;
      if (!workflow) {
        if (vVendor?.invoice_workflow && vVendor.invoice_workflow !== 'BOTH') {
          workflow = vVendor.invoice_workflow;
        } else {
          workflow = 'JOB_WORK';
        }
      }

      await mutateAsync({
        warehouse_id: form.warehouse_id,
        vendor_id: primaryVendorId,
        workflow: workflow && workflow !== 'STANDARD' ? workflow : 'JOB_WORK',
        customer_id: form.customer_id || null,
        po_number: form.po_number || null,
        supplier_document_number: first.invoice_number || first.heat_number || 'PICK',
        supplier_document_date: first.invoice_date ? String(first.invoice_date).trim() : null,
        received_date: first.received_date ? String(first.received_date).trim() : null,
        transporter_name: first.transporter_name ? String(first.transporter_name).trim() : null,
        packing_weight: totalPacking,
        lines: filled.map((line) => {
          const pallets = Math.round(Number(line.pallet_count || 0));
          const per = Number(line.qty_per_pallet || 0);
          return {
            vendor_id: line.vendor_id || primaryVendorId,
            product_id: line.product_id,
            heat_number: (line.heat_number || 'NA').trim(),
            quantity: Number(line.quantity || 0),
            unit_rate: Number(line.unit_rate || 0),
            per_ring_weight: line.per_ring_weight === '' || line.per_ring_weight == null ? undefined : Number(line.per_ring_weight),
            pallet_count: pallets,
            qty_per_pallet: per,
            packing_detail: pallets && per ? `${compactQty(pallets)}*${compactQty(per)}` : undefined,
            source_document_number: line.invoice_number ? String(line.invoice_number).trim() : undefined,
            source_document_date: line.invoice_date ? String(line.invoice_date).trim() : null,
            transporter_name: line.transporter_name ? String(line.transporter_name).trim() : undefined,
            received_date: line.received_date ? String(line.received_date).trim() : null,
            packing_weight: Number(line.packing_weight || 0),
          };
        }),
      });

      navigate('/rings/picks');
    } catch (err) {
      console.error('Pick slip creation error:', err);
      const e = err instanceof Promise ? await err : err;
      const msg = e?.message || e?.details?.message || e?.response?.data?.message || e?.response?.data?.detail || String(e || 'Unknown error');
      window.alert(`Failed to save pick slip:\n${msg}`);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Pick Slip"
        description="Select product, then the inward invoice. Quantity loads in full and can be split across lines up to that invoice remaining qty."
        breadcrumbs={[{ label: 'Picking List', to: '/rings/picks' }, { label: 'New' }]}
      />
      <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="space-y-6">
        <Card>
          <Card.Body className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Warehouse <span className="text-red-500">*</span></label>
              <input type="hidden" {...register('warehouse_id', { required: true })} />
              <SearchableSelect
                value={warehouseId}
                options={warehouses}
                getOptionLabel={(w) => w.name}
                getOptionValue={(w) => w.id}
                placeholder="Select warehouse"
                searchPlaceholder="Search warehouse..."
                className={selectTriggerClass}
                onChange={(id) => setValue('warehouse_id', id, { shouldDirty: true, shouldValidate: true })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Supplier</label>
              <input type="hidden" {...register('vendor_id')} />
              <SearchableSelect
                value={vendorId}
                options={[{ id: '', name: 'All Suppliers (Multi-Supplier)' }, ...vendors]}
                getOptionLabel={(v) => v.name}
                getOptionValue={(v) => v.id}
                placeholder="All Suppliers (or select default)"
                searchPlaceholder="Search supplier..."
                className={selectTriggerClass}
                onChange={(id) => handleSupplierChange(id)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Workflow</label>
              <input type="hidden" {...register('workflow')} />
              <SearchableSelect
                value={workflow || 'JOB_WORK'}
                options={workflowOptions}
                getOptionLabel={(w) => w.name}
                getOptionValue={(w) => w.id}
                placeholder="Select workflow"
                className={selectTriggerClass}
                onChange={(id) => setValue('workflow', id, { shouldDirty: true })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Buyer (Customer)</label>
              <input type="hidden" {...register('customer_id')} />
              <SearchableSelect
                value={customerId}
                options={buyers}
                getOptionLabel={(c) => c.name}
                getOptionValue={(c) => c.id}
                placeholder="Select buyer (optional)"
                searchPlaceholder="Search buyer..."
                className={selectTriggerClass}
                onChange={(id) => setValue('customer_id', id, { shouldDirty: true })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Purchase Order</label>
              <Input
                value={poNumber || ''}
                placeholder="PO number"
                className="h-9 text-sm"
                onChange={(e) => setValue('po_number', e.target.value, { shouldDirty: true })}
              />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Header className="py-2.5 px-3 flex flex-wrap items-center justify-between gap-3 bg-gray-50/50 border-b">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">Available Stock</h3>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 border border-primary-200">
                {displayedStockRows.length} {displayedStockRows.length === 1 ? 'lot' : 'lots'}
              </span>
              {vendor ? (
                <span className="text-xs text-gray-500 ml-2 hidden sm:inline">
                  Default supplier: <strong className="text-gray-800">{vendor.name}</strong>
                </span>
              ) : (
                <span className="text-xs text-emerald-600 font-medium ml-2 hidden sm:inline">
                  Multi-supplier picking enabled
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="w-52">
                <select
                  value={stockSupplierFilter}
                  onChange={(e) => setStockSupplierFilter(e.target.value)}
                  className="w-full h-8 text-xs px-2 bg-white border border-gray-300 rounded-md focus:ring-1 focus:ring-primary-500 focus:border-primary-500 outline-none"
                >
                  <option value="ALL">All Suppliers ({stockRows.length})</option>
                  {vendorsWithStock.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.count})
                    </option>
                  ))}
                </select>
              </div>
              <div className="w-56">
                <Input
                  value={stockSearch}
                  onChange={(e) => setStockSearch(e.target.value)}
                  placeholder="Search SKU, heat, invoice..."
                  className="h-8 text-xs px-2"
                />
              </div>
            </div>
          </Card.Header>
          <Card.Body className="py-2 px-3">
            {isStockLoading ? (
              <p className="text-sm text-gray-500 py-4">Loading stock...</p>
            ) : displayedStockRows.length === 0 ? (
              <p className="text-sm text-gray-500 py-4">No available quantity found matching your filter.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[104rem] text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className={thBase}>Product</th>
                      <th className={thBase}>Invoice Number</th>
                      <th className={thBase}>DATE</th>
                      <th className={thBase}>TRANSPORTER</th>
                      <th className={thBase}>REC.DATE</th>
                      <th className={thBase}>Total Pallets</th>
                      <th className={thBase}>Per Pallet * Qty</th>
                      <th className={thBase}>Total QTY</th>
                      <th className={thBase}>Available</th>
                      <th className={thBase}>Supplier Name</th>
                      <th className={thBase}>Buyer Name</th>
                      <th className={thBase}>Purchase Order Number</th>
                      <th className={thBase}>Heat Number</th>
                      <th className={thBase}>Per Ring Weight</th>
                      <th className={thBase}>Packing Weight</th>
                      <th className={thBase}>Gross Weight</th>
                      <th className={thBase}>Total Weight</th>
                      <th className={`${thBase} text-right sticky right-0 bg-white/95 shadow-sm`}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedStockRows.map((row, index) => {
                      const pallets = Number(row.pallet_count || 0);
                      const per = Number(row.qty_per_pallet || 0);
                      const inwardQty = Number(row.inward_quantity || row.quantity_on_hand || 0);
                      const availableQty = Number(row.quantity_available || 0);
                      const ring = Number(row.per_ring_weight || 0);
                      const pack = Number(row.packing_weight || 0);
                      const gross = grossWeight(availableQty, ring);
                      const total = totalWeight(availableQty, ring, pack);
                      const palletText = pallets > 0 && per > 0
                        ? `${compactQty(pallets)}*${compactQty(per)}`
                        : dash(row.box_qty_text);
                      return (
                        <tr key={`${lotId(row)}-${index}`} className="border-b border-gray-50 hover:bg-gray-50/80 transition-colors">
                          <td className={`${tdBase} font-medium whitespace-nowrap`}>{productLabel(row)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{dash(row.dc_number)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{formatShortDate(row.dc_date)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{dash(row.transporter_name)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{formatShortDate(row.received_date)}</td>
                          <td className={`${tdBase} tabular-nums`}>{formatQty(row.pallet_count)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{palletText}</td>
                          <td className={`${tdBase} tabular-nums`}>{formatQty(inwardQty)}</td>
                          <td className={`${tdBase} tabular-nums font-semibold text-primary-600`}>{formatQty(availableQty)}</td>
                          <td className={`${tdBase} whitespace-nowrap font-medium text-gray-800`}>{dash(row.vendor_name)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{dash(buyer?.name)}</td>
                          <td className={`${tdBase} whitespace-nowrap`}>{dash(poNumber)}</td>
                          <td className={`${tdBase} whitespace-nowrap font-medium`}>{dash(row.heat_number)}</td>
                          <td className={`${tdBase} tabular-nums`}>{dash(row.per_ring_weight)}</td>
                          <td className={`${tdBase} tabular-nums`}>{formatWt(pack)}</td>
                          <td className={`${tdBase} tabular-nums font-medium`}>{formatWt(gross)}</td>
                          <td className={`${tdBase} tabular-nums font-semibold text-gray-900`}>{formatWt(total)}</td>
                          <td className={`${tdBase} text-right whitespace-nowrap sticky right-0 bg-white/95 shadow-sm`}>
                            <Button
                              type="button"
                              size="sm"
                              variant="primary"
                              leftIcon={<Plus className="w-4 h-4" />}
                              className="!px-3 !py-1.5 text-xs font-semibold shadow-sm"
                              onClick={() => handleQuickPick(row)}
                            >
                              Pick
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card.Body>
        </Card>

        <Card>
          <Card.Header className="flex flex-wrap justify-between items-center gap-2 py-3">
            <h3 className="text-base font-medium">Pick lines</h3>
            <Button type="button" variant="secondary" size="sm" onClick={() => append(emptyLine())}>
              <Plus className="w-4 h-4 mr-1" /> Add line
            </Button>
          </Card.Header>
          <Card.Body className="py-2 px-3">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[130rem] table-fixed border-separate border-spacing-y-1">
                <colgroup>
                  <col className="w-[12rem]" />
                  <col className="w-[13rem]" />
                  <col className="w-[6.5rem]" />
                  <col className="w-[9rem]" />
                  <col className="w-[6.5rem]" />
                  <col className="w-[6.5rem]" />
                  <col className="w-[8.5rem]" />
                  <col className="w-[6.5rem]" />
                  <col className="w-[13rem]" />
                  <col className="w-[13rem]" />
                  <col className="w-[10rem]" />
                  <col className="w-[20rem]" />
                  <col className="w-[9rem]" />
                  <col className="w-[8rem]" />
                  <col className="w-[8rem]" />
                  <col className="w-[8rem]" />
                  <col className="w-[2.5rem]" />
                </colgroup>
                <thead>
                  <tr>
                    <th className={thBase}>Product</th>
                    <th className={thBase}>Invoice Number</th>
                    <th className={thBase}>DATE</th>
                    <th className={thBase}>TRANSPORTER</th>
                    <th className={thBase}>REC.DATE</th>
                    <th className={thBase}>Total Pallets</th>
                    <th className={thBase}>Per Pallet * Qty</th>
                    <th className={thBase}>Total QTY</th>
                    <th className={thBase}>Supplier Name</th>
                    <th className={thBase}>Buyer Name</th>
                    <th className={thBase}>Purchase Order Number</th>
                    <th className={thBase}>Heat Number</th>
                    <th className={thBase}>Per Ring Weight</th>
                    <th className={thBase}>Packing Weight</th>
                    <th className={thBase}>Gross Weight</th>
                    <th className={thBase}>Total Weight</th>
                    <th className={thBase} aria-hidden />
                  </tr>
                </thead>
                <tbody>
                  {fields.map((field, index) => {
                    const line = watchedLines[index] || {};
                    const invoices = invoicesForProduct(line.product_id, index, line.vendor_id);
                    const pallets = Number(line.pallet_count || 0);
                    const per = Number(line.qty_per_pallet || 0);
                    const palletText = pallets > 0 && per > 0 ? `${compactQty(pallets)}*${compactQty(per)}` : '—';
                    const qty = Number(line.quantity || 0);
                    const ring = Number(line.per_ring_weight || 0);
                    const pack = Number(line.packing_weight || 0);
                    const gross = grossWeight(qty, ring);
                    const total = totalWeight(qty, ring, pack);
                    const qtyError = lineQtyError(index, line);
                    const perOver = qtyError && (
                      Number(line.qty_per_pallet) > (lineLimit(index, line) ?? Infinity)
                      || (Number(line.pallet_count) > 0 && Number(line.qty_per_pallet) > 0
                        && Number(line.pallet_count) * Number(line.qty_per_pallet) > (lineLimit(index, line) ?? Infinity))
                    );
                    return (
                      <React.Fragment key={field.id}>
                      <tr className="bg-gray-50/80">
                        <td className={`${tdBase} min-w-[12rem]`}>
                          <input type="hidden" {...register(`lines.${index}.product_id`, { required: true })} />
                          <SearchableSelect
                            value={line.product_id || ''}
                            options={getProductOptionsForLine(line)}
                            getOptionLabel={productLabel}
                            getOptionValue={(p) => p.id}
                            placeholder="Select product"
                            searchPlaceholder="Search product..."
                            emptyText="No stock available"
                            className={selectTriggerClass}
                            onChange={(id) => onProductChange(index, id)}
                          />
                        </td>
                        <td className={`${tdBase} min-w-[14rem]`}>
                          <SearchableSelect
                            value={line.lot_id || ''}
                            options={invoices}
                            getOptionLabel={(row) =>
                              [
                                row.dc_number || row.heat_number || 'No invoice',
                                row.dc_date ? formatShortDate(row.dc_date) : null,
                                `Available ${formatQty(row.remaining ?? row.quantity_available)}`,
                              ].filter(Boolean).join(' · ')
                            }
                            getOptionValue={(row) => lotId({ ...row, invoice_number: row.dc_number })}
                            placeholder={line.product_id ? 'Select invoice' : 'Select product first'}
                            searchPlaceholder="Search invoice..."
                            emptyText={line.product_id ? 'No invoice remaining for this product' : 'Select product first'}
                            disabled={!line.product_id}
                            className={selectTriggerClass}
                            onChange={(value) => onInvoiceChange(index, value)}
                          />
                        </td>
                        <td className={`${tdBase} whitespace-nowrap text-sm`}>{formatShortDate(line.invoice_date)}</td>
                        <td className={`${tdBase} whitespace-nowrap text-sm`}>{dash(line.transporter_name)}</td>
                        <td className={`${tdBase} whitespace-nowrap text-sm`}>{formatShortDate(line.received_date)}</td>
                        <td className={tdBase}>
                          <input
                            type="text"
                            inputMode="numeric"
                            className={noSpinnerClass}
                            {...register(`lines.${index}.pallet_count`, { onChange: () => onPalletChange(index) })}
                          />
                        </td>
                        <td className={tdBase}>
                          <input
                            type="text"
                            inputMode="decimal"
                            placeholder="12000"
                            title={qtyError || (palletText !== '—' ? palletText : 'Qty per pallet')}
                            aria-invalid={perOver || undefined}
                            className={`${noSpinnerClass} ${perOver ? 'border-red-500 focus:ring-red-500' : ''}`}
                            {...register(`lines.${index}.qty_per_pallet`, { onChange: () => onPalletChange(index) })}
                          />
                        </td>
                        <td className={tdBase}>
                          <input
                            type="text"
                            inputMode="decimal"
                            title={qtyError && !perOver ? qtyError : undefined}
                            aria-invalid={qtyError && !perOver ? true : undefined}
                            className={`${noSpinnerClass} ${qtyError && !perOver ? 'border-red-500 focus:ring-red-500' : ''}`}
                            {...register(`lines.${index}.quantity`, { required: true })}
                          />
                        </td>
                        <td className={`${tdBase} min-w-[13rem]`}>
                          <SearchableSelect
                            value={line.vendor_id || (vendorId || '')}
                            options={vendors}
                            getOptionLabel={(v) => v.name}
                            getOptionValue={(v) => v.id}
                            placeholder="Select supplier"
                            searchPlaceholder="Search supplier..."
                            className={selectTriggerClass}
                            onChange={(newVId) => {
                              const newV = vendors.find((v) => String(v.id) === String(newVId));
                              setValue(`lines.${index}.vendor_id`, newVId, { shouldDirty: true });
                              setValue(`lines.${index}.vendor_name`, newV?.name || '', { shouldDirty: true });
                              if (line.product_id) {
                                setValue(`lines.${index}.product_id`, '', { shouldDirty: true });
                                setValue(`lines.${index}.lot_id`, '', { shouldDirty: true });
                                setValue(`lines.${index}.invoice_number`, '', { shouldDirty: true });
                                setValue(`lines.${index}.invoice_date`, '', { shouldDirty: true });
                                setValue(`lines.${index}.transporter_name`, '', { shouldDirty: true });
                                setValue(`lines.${index}.received_date`, '', { shouldDirty: true });
                                setValue(`lines.${index}.heat_number`, '', { shouldDirty: true });
                                setValue(`lines.${index}.per_ring_weight`, '', { shouldDirty: true });
                                setValue(`lines.${index}.packing_weight`, '', { shouldDirty: true });
                                setValue(`lines.${index}.quantity`, '', { shouldDirty: true });
                                setValue(`lines.${index}.unit_rate`, '', { shouldDirty: true });
                              }
                            }}
                          />
                        </td>
                        <td className={tdBase}>
                          <SearchableSelect
                            value={customerId}
                            options={buyers}
                            getOptionLabel={(c) => c.name}
                            getOptionValue={(c) => c.id}
                            placeholder="Select buyer"
                            searchPlaceholder="Search buyer..."
                            emptyText="No buyers in Buyer master"
                            className={selectTriggerClass}
                            onChange={(id) => setValue('customer_id', id, { shouldDirty: true })}
                          />
                        </td>
                        <td className={tdBase}>
                          <input
                            type="text"
                            autoComplete="off"
                            placeholder="PO number"
                            className={noSpinnerClass}
                            {...register('po_number')}
                          />
                        </td>
                        <td className={`${tdBase} whitespace-nowrap text-sm font-medium pr-4`}>{dash(line.heat_number)}</td>
                        <td className={`${tdBase} whitespace-nowrap text-sm tabular-nums px-2`}>{dash(line.per_ring_weight)}</td>
                        <td className={tdBase}>
                          <input
                            type="text"
                            inputMode="decimal"
                            placeholder="0"
                            className={noSpinnerClass}
                            {...register(`lines.${index}.packing_weight`)}
                          />
                        </td>
                        <td className={`${tdBase} whitespace-nowrap text-sm tabular-nums font-medium px-2`}>
                          {qty ? formatWt(gross) : '—'}
                        </td>
                        <td className={`${tdBase} whitespace-nowrap text-sm tabular-nums font-semibold text-gray-900 px-2`}>
                          {qty ? formatWt(total) : '—'}
                        </td>
                        <td className={tdBase}>
                          {fields.length > 1 && (
                            <button
                              type="button"
                              className="p-1 text-gray-400 hover:text-red-500"
                              onClick={() => remove(index)}
                              aria-label="Remove line"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                      {qtyError && (
                        <tr>
                          <td colSpan={17} className="px-2 pb-1 text-xs text-red-600 whitespace-nowrap">
                            {perOver ? 'Per Pallet * Qty' : 'Total QTY'}: {qtyError}
                          </td>
                        </tr>
                      )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Add another line to split the same invoice (example 2000, then 500, then 500). Quantity cannot exceed what remains on that invoice.
            </p>
          </Card.Body>
          <Card.Footer className="flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => navigate('/rings/picks')}>Cancel</Button>
            <Button type="submit" isLoading={isPending}>Save pick slip</Button>
          </Card.Footer>
        </Card>
      </form>
    </div>
  );
};

export default RingsPickCreatePage;
