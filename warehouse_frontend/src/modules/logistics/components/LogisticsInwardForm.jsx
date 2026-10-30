import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, useFieldArray, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { logisticsInwardSchema } from '../schemas/logistics.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { Plus, Trash2, Tags, FolderOpen, X, Pencil } from 'lucide-react';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useProducts, useUOMs } from '../../products/hooks/use-products';

const emptyLine = () => ({
  product_id: '',
  quantity: 0,
  uom_id: '',
  lot_number: '',
  unit_rate: 0,
  gst_percent: 18,
  hsn_code: '',
  part_number: '',
  package_count: 0,
  box_count: 0,
  box_quantity: 0,
  has_remark: 'no',
  remarks: '',
});

const isBoxUom = (uomId, uoms) => {
  if (!uomId || !uoms?.length) return false;
  const u = uoms.find((x) => String(x.id) === String(uomId));
  const code = (u?.code || u?.name || '').toUpperCase();
  return code === 'BOX' || code === 'BO' || code.includes('BOX');
};

const matchProductClient = (line, products) => {
  if (!products?.length) return '';
  const guess = (line.sku_guess || line.description || '').toUpperCase();
  const tokens = [];
  const bb = guess.match(/BB1\s*[-\s]?(\d{4})/);
  if (bb) tokens.push(`BB1 ${bb[1]}`, bb[1]);
  if (/6205\s*E\b/.test(guess)) tokens.push('6205 E');
  (guess.match(/\b\d{3,5}\b/g) || []).forEach((n) => tokens.push(n));
  const mm = guess.match(/(\d\.\d{3})\s*MM/);
  if (mm) tokens.push(mm[1]);
  let best = null;
  let bestScore = 0;
  for (const p of products) {
    const s = `${p.sku} ${p.name}`.toUpperCase();
    let score = 0;
    for (const t of tokens) {
      if (s.includes(t)) score += 12;
    }
    if (guess.includes('CAGE') && s.startsWith('CR BB1')) score += 15;
    if (guess.includes('J32P') && s.startsWith('SZ ')) score += 12;
    if (/6205\s*E\b/.test(guess)) {
      if (s.includes('6205 E')) score += 20;
      if (s.startsWith('SZ 6205')) score -= 10;
    }
    if (/6003/.test(guess) && guess.includes('J32P') && p.sku === 'SZ 6003') score += 15;
    if (score > bestScore) {
      bestScore = score;
      best = p;
    }
  }
  return bestScore >= 12 ? best.id : '';
};

const buildAutoLotNumber = (transactionDate, referenceNumber, lineIndex) => {
  const datePart = (transactionDate || new Date().toISOString().slice(0, 10)).replace(/-/g, '');
  const refPart = (referenceNumber || 'INWARD')
    .replace(/[^A-Za-z0-9]/g, '')
    .slice(-10)
    .toUpperCase();
  const seq = String(lineIndex + 1).padStart(2, '0');
  return `LOT-${datePart}-${refPart}-${seq}`;
};

const formatAmount = (n) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number.isFinite(n) ? n : 0
  );

const numInputClass =
  'w-full min-w-0 bg-white border border-gray-200 rounded-md px-1.5 py-1.5 text-sm tabular-nums focus:ring-2 focus:ring-primary-500 outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none';

const numInputRightClass = `${numInputClass} text-right`;
const qtyInputClass =
  'w-full bg-white border border-gray-200 rounded-md px-1.5 py-1.5 text-sm tabular-nums text-right focus:ring-2 focus:ring-primary-500 outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none';

const mapParsedToForm = (parsed, products) => {
  if (!parsed) return null;
  const items =
    parsed.items?.length > 0
      ? parsed.items.map((line, index) => {
          const productId =
            (line.product_id && String(line.product_id)) ||
            matchProductClient(line, products) ||
            '';
          const headerPkg = parsed.package_lines?.[index];
          const partNumber = line.part_number || headerPkg?.part_number || '';
          const packageCount =
            line.package_count ?? headerPkg?.package_count ?? 0;
          return {
            product_id: productId,
            quantity: line.quantity ?? 0,
            uom_id: (line.uom_id && String(line.uom_id)) || '',
            lot_number: line.lot_number || '',
            unit_rate: line.rate ?? line.unit_rate ?? 0,
            gst_percent: 18,
            hsn_code: line.hsn || '',
            part_number: partNumber,
            package_count: packageCount,
            has_remark: 'no',
            box_count: 0,
            box_quantity: 0,
            remarks: productId ? '' : line.description || line.sku_guess || '',
          };
        })
      : [emptyLine()];

  const refType = parsed.reference_document_type || 'OTHER';
  const dateStr = parsed.transaction_date
    ? String(parsed.transaction_date).slice(0, 10)
    : new Date().toISOString().split('T')[0];

  return {
    warehouse_id: '',
    vendor_id: (parsed.vendor_id && String(parsed.vendor_id)) || '',
    reference_document_type: refType,
    reference_document_number: parsed.reference_document_number || parsed.invoice_number || '',
    transaction_date: dateStr,
    remarks: parsed.remarks || '',
    transporter_name: parsed.transporter_name || '',
    vehicle_number: parsed.vehicle_number || '',
    lr_number: parsed.lr_number || '',
    default_gst_percent: 18,
    package_lines: parsed.package_lines || [],
    total_packages: parsed.total_packages ?? null,
    items,
  };
};

const lineSelectClass =
  'w-full bg-white border border-gray-200 rounded-md px-2 py-1.5 text-sm focus:ring-2 focus:ring-primary-500 outline-none';

const LogisticsInwardForm = ({ onSubmit, isLoading, parsedData }) => {
  const { data: warehousesData } = useWarehouses();
  const { data: vendorsData } = useVendors();
  const { data: productsData } = useProducts({ page_size: 200 });
  const { data: uomsData } = useUOMs();

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

  const uoms = useMemo(() => {
    const list = Array.isArray(uomsData) ? uomsData : (uomsData?.items || []);
    return list.slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [uomsData]);

  const [lotPanelOpen, setLotPanelOpen] = useState(false);
  const [remarkModalIndex, setRemarkModalIndex] = useState(null);
  const [remarkDraft, setRemarkDraft] = useState('');
  const remarkRevertRef = useRef({ has_remark: 'no', remarks: '' });

  const productOptions = useMemo(() => {
    const byId = new Map();
    (productsData?.items || []).forEach((p) => byId.set(String(p.id), p));
    (parsedData?.items || []).forEach((line) => {
      if (!line.product_id) return;
      const id = String(line.product_id);
      if (!byId.has(id)) {
        byId.set(id, {
          id,
          sku: line.sku_guess || line.product_name || id,
          name: line.product_name || line.description || line.sku_guess || 'Matched product',
        });
      }
    });
    return Array.from(byId.values()).sort((a, b) => String(a.sku).localeCompare(String(b.sku)));
  }, [productsData?.items, parsedData?.items]);

  const {
    register,
    control,
    handleSubmit,
    reset,
    getValues,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(logisticsInwardSchema),
    defaultValues: {
      warehouse_id: '',
      vendor_id: '',
      reference_document_type: 'PURCHASE_ORDER',
      reference_document_number: '',
      transaction_date: new Date().toISOString().split('T')[0],
      remarks: '',
      transporter_name: '',
      vehicle_number: '',
      lr_number: '',
      default_gst_percent: 18,
      package_lines: [],
      total_packages: null,
      items: [emptyLine()],
    },
  });

  const { fields, append, remove, replace } = useFieldArray({
    control,
    name: 'items',
  });

  const {
    fields: packageFields,
    append: appendPackageLine,
    remove: removePackageLine,
    replace: replacePackageLines,
  } = useFieldArray({
    control,
    name: 'package_lines',
  });

  const watchedItems = useWatch({ control, name: 'items' }) ?? [];
  const defaultGst = useWatch({ control, name: 'default_gst_percent' }) ?? 18;

  const lineTotals = (watchedItems || []).map((row) => {
    const qty = Number(row?.quantity) || 0;
    const rate = Number(row?.unit_rate) || 0;
    const gstPct = Number(row?.gst_percent ?? defaultGst) || 0;
    const taxable = qty * rate;
    const gst = taxable * (gstPct / 100);
    return { taxable, gst, total: taxable + gst };
  });

  const summary = useMemo(() => {
    const taxable = lineTotals.reduce((s, l) => s + l.taxable, 0);
    const gst = lineTotals.reduce((s, l) => s + l.gst, 0);
    return { taxable, gst, grand: taxable + gst };
  }, [lineTotals]);

  const showPricing = useMemo(
    () => lineTotals.some((l) => l.taxable > 0) || Boolean(parsedData?.total_amount),
    [lineTotals, parsedData?.total_amount]
  );

  const lotsReady = useMemo(
    () => (watchedItems || []).some((i) => String(i?.lot_number || '').trim()),
    [watchedItems]
  );

  const lotLines = useMemo(() => {
    const byId = new Map(productOptions.map((p) => [String(p.id), p]));
    return (watchedItems || [])
      .map((row, index) => {
        const lot = String(row?.lot_number || '').trim();
        if (!lot) return null;
        const product = byId.get(String(row.product_id));
        return {
          key: `${index}-${lot}`,
          lot,
          productLabel: product ? `${product.name} (${product.sku})` : `Line ${index + 1}`,
          quantity: row.quantity,
        };
      })
      .filter(Boolean);
  }, [watchedItems, productOptions]);

  const handleCreateLots = () => {
    const items = getValues('items') || [];
    const transactionDate = getValues('transaction_date');
    const referenceNumber = getValues('reference_document_number');
    let filled = 0;
    items.forEach((item, index) => {
      if (!item?.product_id) return;
      if (String(item.lot_number || '').trim()) return;
      setValue(`items.${index}.lot_number`, buildAutoLotNumber(transactionDate, referenceNumber, index), {
        shouldDirty: true,
        shouldValidate: true,
      });
      filled += 1;
    });

    if (filled === 0 && !items.some((i) => String(i?.lot_number || '').trim())) {
      window.alert('Add products first, then click Create lot to generate lot numbers.');
      return;
    }
    setLotPanelOpen(true);
  };

  const handleOpenLot = () => {
    if (!lotLines.length) {
      window.alert('No lots yet. Click Create lot first.');
      return;
    }
    setLotPanelOpen(true);
  };

  const lastParsedKeyRef = useRef(null);

  useEffect(() => {
    const values = mapParsedToForm(parsedData, productOptions);
    if (!values) return;

    const parseKey = JSON.stringify({
      ref: parsedData.reference_document_number || parsedData.invoice_number,
      items: parsedData.items,
    });

    if (lastParsedKeyRef.current !== parseKey) {
      lastParsedKeyRef.current = parseKey;
      reset(values);
      replace(values.items);
      if (values.package_lines?.length) {
        replacePackageLines(values.package_lines);
      }
      return;
    }

    values.items.forEach((mapped, index) => {
      if (!mapped.product_id) return;
      const current = getValues(`items.${index}.product_id`);
      if (!current) {
        setValue(`items.${index}.product_id`, mapped.product_id, { shouldDirty: true });
      }
    });
  }, [parsedData, productOptions, reset, replace, replacePackageLines, getValues, setValue]);

  const totalPackages = watch('total_packages');

  const recalcBoxLineQty = (index) => {
    queueMicrotask(() => {
      const uomId = getValues(`items.${index}.uom_id`);
      if (!isBoxUom(uomId, uomsData)) return;
      const boxes = Number(getValues(`items.${index}.box_count`)) || 0;
      const perBox = Number(getValues(`items.${index}.box_quantity`)) || 0;
      if (boxes > 0 && perBox > 0) {
        setValue(`items.${index}.quantity`, boxes * perBox, {
          shouldValidate: true,
          shouldDirty: true,
          shouldTouch: true,
        });
      }
    });
  };

  const openRemarkModal = (index, fromYesSelect = false) => {
    const remarks = getValues(`items.${index}.remarks`) || '';
    const hasRemark = getValues(`items.${index}.has_remark`) || 'no';
    remarkRevertRef.current = fromYesSelect
      ? { has_remark: 'no', remarks: '' }
      : { has_remark: hasRemark, remarks };
    setRemarkModalIndex(index);
    setRemarkDraft(remarks);
  };

  const closeRemarkModal = (revert) => {
    if (remarkModalIndex == null) return;
    if (revert) {
      const { has_remark, remarks } = remarkRevertRef.current;
      setValue(`items.${remarkModalIndex}.has_remark`, has_remark, { shouldDirty: true });
      setValue(`items.${remarkModalIndex}.remarks`, remarks, { shouldDirty: true });
    }
    setRemarkModalIndex(null);
    setRemarkDraft('');
  };

  const saveRemarkModal = () => {
    if (remarkModalIndex == null) return;
    const text = remarkDraft.trim();
    if (!text) {
      window.alert('Please enter remark text.');
      return;
    }
    setValue(`items.${remarkModalIndex}.remarks`, text, { shouldDirty: true, shouldValidate: true });
    setValue(`items.${remarkModalIndex}.has_remark`, 'yes', { shouldDirty: true });
    setRemarkModalIndex(null);
    setRemarkDraft('');
  };

  const submitInward = (data) => {
    const { default_gst_percent: _dg, ...rest } = data;
    onSubmit({
      ...rest,
      package_lines: (data.package_lines || []).filter((r) => r.part_number?.trim()),
      total_packages: (() => {
        if (data.total_packages != null && data.total_packages !== '') {
          return Number(data.total_packages);
        }
        const sum = (data.package_lines || []).reduce(
          (s, r) => s + (Number(r.package_count) || 0),
          0
        );
        return sum > 0 ? sum : undefined;
      })(),
      items: data.items.map(
        ({
          unit_rate,
          gst_percent,
          expiry_date,
          hsn_code,
          part_number,
          package_count,
          has_remark,
          box_count,
          box_quantity,
          remarks,
          uom_id,
          ...line
        }) => {
          const uomIsBox = isBoxUom(uom_id, uomsData);
          const boxes = Number(box_count) || 0;
          const perBox = Number(box_quantity) || 0;
          let lineRemarks = has_remark === 'yes' && remarks?.trim() ? remarks.trim() : undefined;
          if (uomIsBox && boxes > 0 && perBox > 0) {
            const boxNote = `Boxes: ${boxes} × ${perBox} = ${boxes * perBox}`;
            lineRemarks = lineRemarks ? `${lineRemarks} | ${boxNote}` : boxNote;
          }
          const pkg =
            package_count != null && String(package_count) !== ''
              ? Number(package_count)
              : undefined;
          return {
            ...line,
            uom_id,
            remarks: lineRemarks,
            unit_cost: unit_rate && unit_rate > 0 ? unit_rate : undefined,
            hsn_code: hsn_code?.trim() ? hsn_code.trim() : undefined,
            part_number: part_number?.trim() ? part_number.trim() : undefined,
            package_count: pkg,
            lot_number: line.lot_number?.trim() ? line.lot_number : undefined,
          };
        }
      ),
    });
  };

  const remarkEditSlotClass = 'shrink-0 w-[22px]';
  const thBase =
    'px-1 py-1.5 text-[10px] font-semibold text-gray-400 uppercase leading-tight align-middle text-center whitespace-nowrap';
  const tdBase = 'px-1 py-1.5 align-middle';
  const tdR = `${tdBase} text-right`;
  const tdAmount = `${tdBase} text-center tabular-nums`;
  const itemRowTrClass =
    'bg-gray-50/80 [&>td:first-child]:rounded-l-md [&>td:last-child]:rounded-r-md border-y border-gray-100';

  return (
    <form onSubmit={handleSubmit(submitInward)} className="space-y-4">
      <Card>
        <Card.Header className="py-3">
          <h3 className="text-base font-medium">Header Information</h3>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-3 py-3">
          <div className="space-y-1">
            <label htmlFor="warehouse_id" className="text-xs font-medium text-gray-600">Warehouse</label>
            <select id="warehouse_id" {...register('warehouse_id')} className={lineSelectClass}>
              <option value="">Select Warehouse</option>
              {warehouses.map((wh) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </select>
            {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
          </div>

          <div className="space-y-1">
            <label htmlFor="vendor_id" className="text-xs font-medium text-gray-600">Supplier</label>
            <select id="vendor_id" {...register('vendor_id')} className={lineSelectClass}>
              <option value="">Select Supplier</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>

          <Input
            label="Transaction Date"
            type="date"
            className="py-1.5 text-sm"
            error={errors.transaction_date?.message}
            isRequired
            {...register('transaction_date')}
          />

          <div className="space-y-1">
            <label htmlFor="reference_document_type" className="text-xs font-medium text-gray-600">Reference Type</label>
            <select id="reference_document_type" {...register('reference_document_type')} className={lineSelectClass}>
              <option value="PURCHASE_ORDER">Purchase Order</option>
              <option value="STOCK_TRANSFER">Stock Transfer</option>
              <option value="RETURN">Customer Return</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <Input
            label="Reference Number"
            placeholder="PO-2026-001"
            className="py-1.5 text-sm"
            error={errors.reference_document_number?.message}
            isRequired
            {...register('reference_document_number')}
          />

          <Input label="Transporter" className="py-1.5 text-sm" {...register('transporter_name')} />
          <Input label="Vehicle" className="py-1.5 text-sm" {...register('vehicle_number')} />
          <Input label="LR / GR" className="py-1.5 text-sm" {...register('lr_number')} />

          <div className="md:col-span-3 space-y-1">
            <label htmlFor="remarks" className="text-xs font-medium text-gray-600">Remarks</label>
            <textarea
              id="remarks"
              rows={2}
              className="w-full bg-white border border-gray-200 rounded-md px-3 py-1.5 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              {...register('remarks')}
            />
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="flex flex-wrap justify-between items-center gap-2 py-3">
          <h3 className="text-base font-medium">Items</h3>
          <div className="flex items-center gap-2">
            {lotsReady ? (
              <Button type="button" variant="secondary" size="sm" onClick={handleOpenLot}>
                <FolderOpen className="w-4 h-4 mr-1" /> Open lot
              </Button>
            ) : (
              <Button type="button" variant="secondary" size="sm" onClick={handleCreateLots}>
                <Tags className="w-4 h-4 mr-1" /> Create lot
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => append(emptyLine())}
            >
              <Plus className="w-4 h-4 mr-1" /> Add Item
            </Button>
          </div>
        </Card.Header>
        <Card.Body className="py-2 px-3">
          <div className="overflow-x-auto -mx-1 px-1">
          <div className="min-w-[92rem] px-1">
          <table className="w-full table-fixed border-separate border-spacing-y-1.5">
            <colgroup>
              <col className="w-[22%]" />
              <col className="w-[6%]" />
              <col className="w-[7%]" />
              <col className="w-[5%]" />
              <col className="w-[6%]" />
              <col className="w-[10%]" />
              <col className="w-[4%]" />
              <col className="w-[5%]" />
              <col className="w-[5.5%]" />
              <col className="w-[6%]" />
              <col className="w-[4%]" />
              <col className="w-[8%]" />
              <col className="w-[8%]" />
              <col className="w-[2.5%]" />
            </colgroup>
            <thead>
              <tr>
                <th className={thBase}>Product</th>
                <th className={thBase}>Part No.</th>
                <th className={thBase}>
                  <div className="inline-flex items-center justify-center gap-0.5 mx-auto">
                    <span>Remark</span>
                    <span className={remarkEditSlotClass} aria-hidden />
                  </div>
                </th>
                <th className={thBase}>Pkgs</th>
                <th className={thBase}>HSN</th>
                <th className={thBase}>Qty</th>
                <th className={thBase}>UOM</th>
                <th className={thBase}>Boxes</th>
                <th className={thBase}>Box Qty</th>
                <th className={thBase}>Rate</th>
                <th className={thBase}>GST%</th>
                <th className={thBase}>Taxable ₹</th>
                <th className={thBase}>Total ₹</th>
                <th className={thBase} aria-hidden />
              </tr>
            </thead>
            <tbody>
            {fields.map((field, index) => {
              const lineUomId = watchedItems?.[index]?.uom_id;
              const lineHasRemark = watchedItems?.[index]?.has_remark === 'yes';
              const lineIsBox = isBoxUom(lineUomId, uomsData);
              return (
              <tr key={field.id} className={itemRowTrClass}>
                <td className={tdBase}>
                  <input type="hidden" {...register(`items.${index}.lot_number`)} />
                  <select
                    id={`items.${index}.product_id`}
                    {...register(`items.${index}.product_id`)}
                    className={lineSelectClass}
                  >
                    <option value="">Select Product</option>
                    {productOptions.map((p) => (
                      <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                    ))}
                  </select>
                  {errors.items?.[index]?.product_id && (
                    <p className="text-[10px] text-red-500 mt-0.5">{errors.items[index].product_id.message}</p>
                  )}
                </td>

                <td className={tdBase}>
                  <input
                    type="text"
                    autoComplete="off"
                    placeholder="Part no."
                    className={numInputClass}
                    {...register(`items.${index}.part_number`)}
                  />
                </td>

                <td className={tdBase}>
                  <input type="hidden" {...register(`items.${index}.remarks`)} />
                  <div className="flex items-center gap-0.5">
                    <select
                      className={`${lineSelectClass} flex-1 min-w-0 py-1 pl-1.5 pr-1 text-xs`}
                      title={
                        errors.items?.[index]?.remarks?.message ||
                        (lineHasRemark && watchedItems?.[index]?.remarks?.trim()
                          ? watchedItems[index].remarks
                          : undefined)
                      }
                      {...register(`items.${index}.has_remark`, {
                        onChange: (e) => {
                          const v = e.target.value;
                          if (v === 'yes') {
                            openRemarkModal(index, true);
                          } else {
                            setValue(`items.${index}.remarks`, '', { shouldDirty: true });
                          }
                        },
                      })}
                    >
                      <option value="no">No</option>
                      <option value="yes">Yes</option>
                    </select>
                    {lineHasRemark ? (
                      <button
                        type="button"
                        className={`${remarkEditSlotClass} p-0.5 rounded text-primary-600 hover:bg-primary-50 flex items-center justify-center`}
                        onClick={() => openRemarkModal(index, false)}
                        title={
                          watchedItems?.[index]?.remarks?.trim() || 'Edit remark'
                        }
                        aria-label="Edit remark"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <span className={remarkEditSlotClass} aria-hidden />
                    )}
                  </div>
                </td>

                <td className={tdR}>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="0"
                    className={numInputRightClass}
                    {...register(`items.${index}.package_count`, { valueAsNumber: true })}
                  />
                </td>

                <td className={tdBase}>
                  <input
                    type="text"
                    autoComplete="off"
                    placeholder="HSN"
                    className={numInputClass}
                    {...register(`items.${index}.hsn_code`)}
                  />
                </td>

                <td className={tdR}>
                  <input
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    className={qtyInputClass}
                    {...register(`items.${index}.quantity`, { valueAsNumber: true })}
                  />
                </td>

                <td className={`${tdBase} text-center`}>
                  <select
                    {...register(`items.${index}.uom_id`, {
                      onChange: (e) => {
                        if (!isBoxUom(e.target.value, uomsData)) {
                          setValue(`items.${index}.box_count`, 0);
                          setValue(`items.${index}.box_quantity`, 0);
                        }
                      },
                    })}
                    className={lineSelectClass}
                  >
                    <option value="">UOM</option>
                    {uoms.map((u) => (
                      <option key={u.id} value={u.id}>{u.code}</option>
                    ))}
                  </select>
                </td>

                <td className={tdR}>
                {lineIsBox ? (
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="0"
                    className={numInputRightClass}
                    {...register(`items.${index}.box_count`, {
                      valueAsNumber: true,
                      onChange: () => recalcBoxLineQty(index),
                      onBlur: () => recalcBoxLineQty(index),
                    })}
                  />
                ) : (
                  <span className="text-gray-300 text-right text-xs tabular-nums block">—</span>
                )}
                </td>

                <td className={tdR}>
                {lineIsBox ? (
                  <input
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    placeholder="0"
                    className={numInputRightClass}
                    {...register(`items.${index}.box_quantity`, {
                      valueAsNumber: true,
                      onChange: () => recalcBoxLineQty(index),
                      onBlur: () => recalcBoxLineQty(index),
                    })}
                  />
                ) : (
                  <span className="text-gray-300 text-right text-xs tabular-nums block">—</span>
                )}
                </td>

                <td className={tdR}>
                  <input
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    placeholder="0"
                    className={numInputRightClass}
                    {...register(`items.${index}.unit_rate`, { valueAsNumber: true })}
                  />
                </td>

                <td className={tdR}>
                  <input
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    className={numInputRightClass}
                    {...register(`items.${index}.gst_percent`, { valueAsNumber: true })}
                  />
                </td>

                <td className={`${tdAmount} text-xs text-gray-600`}>
                  {formatAmount(lineTotals[index]?.taxable ?? 0)}
                </td>

                <td className={`${tdAmount} text-sm font-medium text-gray-900`}>
                  {formatAmount(lineTotals[index]?.total ?? 0)}
                </td>

                <td className={`${tdBase} text-center`}>
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    className="p-1 text-gray-400 hover:text-red-500 inline-flex"
                    disabled={fields.length === 1}
                    aria-label="Remove line"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            );
            })}
            </tbody>
          </table>
          </div>
          </div>

          {errors.items?.message && <p className="text-sm text-red-500 mt-2">{errors.items.message}</p>}

          {(showPricing || parsedData?.total_amount) && (
            <div className="mt-3 pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:justify-end gap-3 text-sm">
              <div className="space-y-1 sm:text-right min-w-[220px]">
                <div className="flex justify-between sm:justify-end gap-4 text-gray-600">
                  <span>Taxable value (₹)</span>
                  <span className="tabular-nums">{formatAmount(summary.taxable)}</span>
                </div>
                <div className="flex justify-between sm:justify-end gap-4 text-gray-600">
                  <span>GST (₹)</span>
                  <span className="tabular-nums">{formatAmount(summary.gst)}</span>
                </div>
                <div className="flex justify-between sm:justify-end gap-4 font-semibold text-gray-900">
                  <span>Total (₹)</span>
                  <span className="tabular-nums">{formatAmount(summary.grand)}</span>
                </div>
                {parsedData?.total_amount != null && (
                  <div className="flex justify-between sm:justify-end gap-4 text-xs text-gray-500 pt-1">
                    <span>Invoice total (PDF) (₹)</span>
                    <span className="tabular-nums">{formatAmount(parsedData.total_amount)}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <p className="text-[11px] text-gray-400 mt-2">
            <strong>HSN</strong>, <strong>Part No.</strong>, and <strong>Pkgs</strong> can be typed on each line (or filled from PDF).
            Stored on post: HSN → product master; part/pkgs → receipt remarks + line remarks. Use <strong>Open lot</strong> for invoice package list.
          </p>
        </Card.Body>
        <Card.Footer className="flex justify-end gap-2 py-3">
          <Button type="button" variant="secondary" size="sm" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={isLoading}>
            Post Inward
          </Button>
        </Card.Footer>
      </Card>

      {remarkModalIndex != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
          <Card className="w-full max-w-md shadow-xl">
            <Card.Header className="flex items-center justify-between py-3">
              <h3 className="text-base font-semibold">
                Line {remarkModalIndex + 1} remark
              </h3>
              <button
                type="button"
                className="p-1 text-gray-400 hover:text-gray-600"
                onClick={() => closeRemarkModal(true)}
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </Card.Header>
            <Card.Body className="space-y-3">
              <textarea
                className="w-full min-h-[100px] border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="Enter remark for this product line..."
                value={remarkDraft}
                onChange={(e) => setRemarkDraft(e.target.value)}
                autoFocus
              />
            </Card.Body>
            <Card.Footer className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => closeRemarkModal(true)}
              >
                Cancel
              </Button>
              <Button type="button" size="sm" onClick={saveRemarkModal}>
                Save remark
              </Button>
            </Card.Footer>
          </Card>
        </div>
      )}

      {lotPanelOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
          <Card className="w-full max-w-lg shadow-xl">
            <Card.Header className="flex items-center justify-between py-3">
              <h3 className="text-base font-semibold">Lots for this inward</h3>
              <button
                type="button"
                className="p-1 text-gray-400 hover:text-gray-600"
                onClick={() => setLotPanelOpen(false)}
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </Card.Header>
            <Card.Body className="p-0 max-h-[60vh] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="text-left px-4 py-2">Product</th>
                    <th className="text-left px-4 py-2">Lot number</th>
                    <th className="text-right px-4 py-2">Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {lotLines.map((row) => (
                    <tr key={row.key} className="border-t border-gray-100">
                      <td className="px-4 py-2 text-gray-800">{row.productLabel}</td>
                      <td className="px-4 py-2">
                        <Link
                          to={`/inventory/lots/${encodeURIComponent(row.lot)}`}
                          className="text-primary-600 hover:underline font-medium break-all"
                          onClick={() => setLotPanelOpen(false)}
                        >
                          {row.lot}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">{row.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!lotLines.length && (
                <p className="text-center text-gray-500 py-6 text-sm">No lots generated yet.</p>
              )}

              <div className="border-t border-gray-100 px-4 py-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase">
                    Invoice Part No. / pkgs (header)
                    {totalPackages != null ? ` · total ${totalPackages}` : ''}
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => appendPackageLine({ part_number: '', package_count: 0 })}
                  >
                    <Plus className="w-3 h-3 mr-1" /> Add row
                  </Button>
                </div>
                {packageFields.length > 0 ? (
                  <div className="space-y-2">
                    {packageFields.map((pkg, idx) => (
                      <div key={pkg.id} className="flex gap-2 items-center">
                        <input
                          className={`${numInputClass} flex-1`}
                          placeholder="Part No."
                          {...register(`package_lines.${idx}.part_number`)}
                        />
                        <input
                          className={`${numInputClass} w-20 text-right`}
                          inputMode="numeric"
                          placeholder="Pkgs"
                          {...register(`package_lines.${idx}.package_count`, { valueAsNumber: true })}
                        />
                        <button
                          type="button"
                          className="p-1 text-gray-400 hover:text-red-500"
                          onClick={() => removePackageLine(idx)}
                          aria-label="Remove"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">No header rows — add manually or upload Manu PDF.</p>
                )}
                <p className="text-[10px] text-gray-400 mt-2">
                  Saved in DB on <strong>stock_transactions.remarks</strong> as JSON when you Post Inward.
                </p>
              </div>
            </Card.Body>
            <Card.Footer className="flex justify-between items-center gap-2 py-3 text-xs text-gray-500">
              <span>Stock appears after you Post Inward.</span>
              <Button type="button" size="sm" variant="secondary" onClick={() => setLotPanelOpen(false)}>
                Close
              </Button>
            </Card.Footer>
          </Card>
        </div>
      )}
    </form>
  );
};

export default LogisticsInwardForm;
