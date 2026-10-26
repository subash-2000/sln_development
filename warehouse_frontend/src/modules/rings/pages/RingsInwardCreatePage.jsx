import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Plus, Trash2, Pencil, X } from 'lucide-react';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import Input from '../../../components/ui/Input';
import SearchableSelect from '../../../components/ui/SearchableSelect';
import InwardDocumentUpload from '../../logistics/components/InwardDocumentUpload';
import { useProducts, useUOMs } from '../../products/hooks/use-products';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import { useCreateRingsInward, useRingsSupplierTypes } from '../hooks/use-rings';

const emptyLine = () => ({
  product_id: '',
  heat_number: '',
  packing_ratio: '',
  has_remark: 'no',
  remarks: '',
  pallet_count: 0,
  qty_per_pallet: 0,
  box_count: 0,
  qty_per_box: 0,
  quantity: 0,
  short_quantity: '',
  unit_rate: 0,
  gst_percent: 0,
  per_ring_weight: '',
  packing_weight: '',
  challan_number: '',
  reference_number: '',
  part_number: '',
});

const toDateInput = (value) => (value ? String(value).slice(0, 10) : '');

const isPlausibleRefNo = (value) => {
  const s = String(value ?? '').trim();
  if (!/^\d{2,6}$/.test(s)) return false;
  if (s.length > 6) return false;
  if (s.startsWith('84') || s.startsWith('8482')) return false;
  return true;
};

/** PDF sometimes maps HSN (84829900) into ref — use challan suffix (e.g. DC252600257 → 0257). */
const resolveParsedRefNo = (line, challanNumber) => {
  const hsn = String(line.hsn ?? '').trim();
  for (const raw of [line.reference_number, line.reference_no]) {
    const s = String(raw ?? '').trim();
    if (!s || s === hsn) continue;
    if (isPlausibleRefNo(s)) return s;
  }
  const challan = String(challanNumber || line.challan_number || line.source_document_number || '').trim();
  const m = challan.match(/(\d{4})$/i);
  return m ? m[1] : '';
};

const buildPackingDetail = (line) => {
  const ratio = String(line?.packing_ratio || '').trim();
  const boxes = Number(line?.box_count || 0);
  const perBox = Number(line?.qty_per_box || 0);
  const pallets = Number(line?.pallet_count || 0);
  const perPallet = Number(line?.qty_per_pallet || 0);
  const qty = packingQty(line) || Number(line?.quantity || 0);
  if (ratio && boxes && perBox && !pallets) {
    return `${perBox}x${boxes} = ${qty} (${ratio})`.slice(0, 100);
  }
  if (ratio && pallets && perPallet && !boxes) {
    return `${perPallet}x${pallets} = ${qty} (${ratio})`.slice(0, 100);
  }
  return ratio || undefined;
};

const formatAmount = (n) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number.isFinite(n) ? n : 0
  );

const formatWt = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v)) return '—';
  return v.toFixed(3);
};

const lineGrossWeight = (qty, ringWt) => (Number(qty) || 0) * (Number(ringWt) || 0);

const lineTotalWeight = (qty, ringWt, packingWt) =>
  lineGrossWeight(qty, ringWt) + (Number(packingWt) || 0);

const formatPackingWtInput = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return '';
  if (n === 0) return '0';
  return n.toFixed(3);
};

/** PDF header packing → line fields (editable after); per-line values win when present. */
const applyParsedPackingWeights = (lines, parsedData) => {
  if (!lines?.length || !parsedData) return lines;
  const srcItems = parsedData.items || [];
  const hasLinePack = srcItems.some((i) => Number(i.packing_weight) > 0);
  if (hasLinePack) {
    return lines.map((line, idx) => ({
      ...line,
      packing_weight: formatPackingWtInput(srcItems[idx]?.packing_weight ?? line.packing_weight),
    }));
  }
  const docPack = Number(parsedData.packing_weight);
  if (!Number.isFinite(docPack) || docPack <= 0) return lines;
  const qtys = lines.map((line) => packingQty(line) || Number(line.quantity) || 0);
  const totalQty = qtys.reduce((sum, q) => sum + q, 0);
  if (lines.length === 1) {
    return [{ ...lines[0], packing_weight: formatPackingWtInput(docPack) }];
  }
  if (totalQty <= 0) {
    return lines.map((line, idx) =>
      idx === 0 ? { ...line, packing_weight: formatPackingWtInput(docPack) } : line
    );
  }
  return lines.map((line, idx) => ({
    ...line,
    packing_weight: formatPackingWtInput(docPack * (qtys[idx] / totalQty)),
  }));
};

const lineSelectClass =
  'w-full bg-white border border-gray-200 rounded-md px-2 py-1.5 text-sm focus:ring-2 focus:ring-primary-500 outline-none';
const numInputClass =
  'w-full min-w-0 bg-white border border-gray-200 rounded-md px-1.5 py-1.5 text-sm tabular-nums focus:ring-2 focus:ring-primary-500 outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none';
const challanColClass = 'w-[7.75rem] max-w-[7.75rem]';
const challanInputClass =
  'bg-white border border-gray-200 rounded-md px-1 py-1.5 font-mono text-[11px] leading-tight tracking-tight tabular-nums focus:ring-2 focus:ring-primary-500 outline-none w-full min-w-0';
const lineProductSelectClass =
  'max-w-full h-8 text-xs px-1.5';
const numInputRightClass = `${numInputClass} text-right`;
const thBase =
  'px-1 py-1.5 text-[10px] font-semibold text-gray-400 uppercase leading-tight align-middle text-center whitespace-nowrap';
const tdBase = 'px-1 py-1.5 align-middle';
const tdR = `${tdBase} text-right`;
const tdAmount = `${tdBase} text-center tabular-nums`;
const itemRowTrClass =
  'bg-gray-50/80 [&>td:first-child]:rounded-l-md [&>td:last-child]:rounded-r-md border-y border-gray-100';
const remarkEditSlotClass = 'shrink-0 w-[22px]';

const packingQty = (line) =>
  Number(line?.pallet_count || 0) * Number(line?.qty_per_pallet || 0) +
  Number(line?.box_count || 0) * Number(line?.qty_per_box || 0);

const parseShortQty = (value) => {
  if (value === '' || value == null) return 0;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : 0;
};

/** Net received = packed (or manual qty) minus short / damage. */
const lineNetQty = (line) => {
  const gross = packingQty(line);
  const short = parseShortQty(line?.short_quantity);
  if (gross > 0) return Math.max(0, gross - short);
  const manual = Number(line?.quantity) || 0;
  return Math.max(0, manual - short);
};

const formatHsnDisplay = (code) => {
  const s = String(code ?? '').trim();
  if (!s) return '—';
  const n = Number(s);
  if (Number.isFinite(n) && n > 0) return String(Math.trunc(n));
  return s.replace(/\.0+$/, '');
};

const matchProduct = (line, products) => {
  if (!products?.length) return '';
  if (line?.product_id) {
    const byId = products.find((p) => String(p.id) === String(line.product_id));
    if (byId) return String(byId.id);
  }
  const partNo = String(line?.part_number || '').trim();
  if (partNo) {
    const byPart = products.find((p) => String(p.part_number || '').trim() === partNo);
    if (byPart) return String(byPart.id);
  }
  const guess = `${line?.sku_guess || ''} ${line?.product_name || ''} ${line?.description || ''}`.toUpperCase();
  if (!guess.trim()) return '';
  const compact = guess.replace(/\s+/g, '');
  const digits = [...new Set(guess.match(/\b\d{3,5}\b/g) || [])];
  const prefersOm = /\bOR\b|ORPOYO|OUTER/.test(guess) || compact.includes('ORPOYO');
  const prefersIm = /\bIR\b|INNER/.test(guess) || compact.includes('IRPOYO');

  const exact = products.find((p) => {
    const sku = String(p.sku || '').toUpperCase();
    const name = String(p.name || '').toUpperCase();
    return (sku && guess.includes(sku)) || (name && guess.includes(name));
  });
  if (exact) return String(exact.id);

  let best = null;
  let bestScore = 0;
  products.forEach((p) => {
    const sku = String(p.sku || '').toUpperCase();
    const name = String(p.name || '').toUpperCase();
    const blob = `${sku}${name}`.replace(/\s+/g, '');
    let score = 0;
    digits.forEach((d) => {
      if (blob.includes(d)) score += 12;
    });
    if (prefersOm && sku.startsWith('OM')) score += 22;
    if (prefersIm && sku.startsWith('IM')) score += 22;
    if (score > bestScore) {
      bestScore = score;
      best = p;
    }
  });
  return bestScore >= 12 ? String(best.id) : '';
};

const productLabel = (product) => {
  const sku = String(product?.sku || '').trim();
  const name = String(product?.name || '').trim();
  if (!name || !sku || name.toUpperCase() === sku.toUpperCase()) return sku || name || 'Product';
  return `${sku} — ${name}`;
};

const RingsInwardCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync, isPending } = useCreateRingsInward();
  const [parsedData, setParsedData] = useState(null);
  const lastParseKeyRef = useRef(null);
  const [remarkModalIndex, setRemarkModalIndex] = useState(null);
  const [remarkDraft, setRemarkDraft] = useState('');
  const remarkRevertRef = useRef({ has_remark: 'no', remarks: '' });
  const { data: warehousesData } = useWarehouses();
  const { data: vendorsData } = useVendors({ page_size: 200, status: 'ACTIVE' });
  const { data: uomsData } = useUOMs();
  const warehouses = warehousesData?.items || [];
  const vendors = vendorsData?.items || [];

  const { register, control, handleSubmit, watch, setValue, getValues, reset } = useForm({
    shouldUnregister: true,
    defaultValues: {
      warehouse_id: '',
      vendor_id: '',
      workflow: '',
      supplier_document_number: '',
      supplier_document_date: new Date().toISOString().slice(0, 10),
      reference_date: '',
      received_date: new Date().toISOString().slice(0, 10),
      transporter_name: '',
      vehicle_number: '',
      lr_number: '',
      lr_date: '',
      po_number: '',
      remarks: '',
      lines: [emptyLine()],
    },
  });
  const { fields, append, remove, replace } = useFieldArray({ control, name: 'lines' });
  const vendorId = watch('vendor_id');
  const watchedLines = useWatch({ control, name: 'lines' }) || [];
  const { data: supplierTypes, isFetched: typesFetched } = useRingsSupplierTypes(vendorId);
  const { data: catalogData } = useProducts(
    { page_size: 200, vendor_id: vendorId },
    { enabled: !!vendorId, placeholderData: null }
  );
  const vendor = useMemo(() => vendors.find((v) => v.id === vendorId), [vendors, vendorId]);
  const workflowMaster = vendor?.invoice_workflow || 'STANDARD';
  const isDirect = (watch('workflow') || workflowMaster) === 'DIRECT_INVOICE';

  const productOptions = useMemo(() => {
    if (!vendorId) return [];
    const types = Array.isArray(supplierTypes) ? supplierTypes : [];
    if (types.length) {
      const seen = new Set();
      return types.flatMap((t) => {
        const id = String(t.product_id);
        if (seen.has(id)) return [];
        seen.add(id);
        return [{
          id: t.product_id,
          sku: t.product_sku,
          name: t.product_name || t.product_sku,
          uom_id: t.uom_id,
          net_weight: t.per_ring_weight,
          unit_rate: t.unit_rate,
          packing_ratio: t.packing_ratio,
        }];
      });
    }
    return catalogData?.items || [];
  }, [vendorId, supplierTypes, catalogData]);

  useEffect(() => {
    const ringsWh = warehouses.find((w) => w.code === 'RING-GDN') || warehouses[0];
    if (ringsWh && !getValues('warehouse_id')) setValue('warehouse_id', ringsWh.id);
  }, [warehouses, setValue, getValues]);

  useEffect(() => {
    if (!vendorId) {
      (getValues('lines') || []).forEach((_, index) => {
        setValue(`lines.${index}.product_id`, '');
        setValue(`lines.${index}.per_ring_weight`, '');
      });
      return;
    }
    if (!typesFetched || !productOptions.length) return;
    const allowed = new Set(productOptions.map((p) => String(p.id)));
    (getValues('lines') || []).forEach((line, index) => {
      if (line?.product_id && !allowed.has(String(line.product_id))) {
        setValue(`lines.${index}.product_id`, '');
        setValue(`lines.${index}.per_ring_weight`, '');
      }
    });
  }, [vendorId, typesFetched, productOptions, getValues, setValue]);

  useEffect(() => {
    if (!parsedData) return;
    const parseKey = JSON.stringify({
      ref: parsedData.reference_document_number || parsedData.invoice_number,
      items: parsedData.items,
      packing_weight: parsedData.packing_weight,
      reference_date: parsedData.reference_date,
      lr_date: parsedData.lr_date,
      lr_number: parsedData.lr_number,
    });
    if (lastParseKeyRef.current === parseKey) return;
    lastParseKeyRef.current = parseKey;

    const dateStr = parsedData.transaction_date
      ? String(parsedData.transaction_date).slice(0, 10)
      : getValues('supplier_document_date');
    const mappedLinesRaw = (parsedData.items || []).length
      ? parsedData.items.map((line) => {
          const productId = matchProduct(line, productOptions);
          const product = productOptions.find((p) => String(p.id) === String(productId));
          const qty = Number(line.quantity ?? 0);
          const boxes = Number(line.box_count ?? line.package_count ?? 0);
          let perBox = Number(line.qty_per_box ?? line.box_quantity ?? 0);
          if (!perBox && boxes > 0 && qty > 0) perBox = qty / boxes;
          const pallets = Number(line.pallet_count ?? 0);
          const perPallet = Number(line.qty_per_pallet ?? 0);
          return {
            ...emptyLine(),
            product_id: productId,
            heat_number: line.lot_number || line.heat_number || '',
            packing_ratio: line.packing_ratio || product?.packing_ratio || '',
            has_remark: line.remarks ? 'yes' : 'no',
            remarks: line.remarks || '',
            pallet_count: pallets,
            qty_per_pallet: perPallet,
            box_count: boxes,
            qty_per_box: perBox,
            quantity: qty || (boxes && perBox ? boxes * perBox : 0),
            short_quantity: '',
            unit_rate: line.rate ?? line.unit_rate ?? 0,
            per_ring_weight: product?.net_weight ?? '',
            packing_weight: formatPackingWtInput(line.packing_weight),
            challan_number:
              line.challan_number ||
              line.source_document_number ||
              parsedData.reference_document_number ||
              '',
            reference_number: resolveParsedRefNo(
              line,
              line.challan_number ||
                line.source_document_number ||
                parsedData.reference_document_number
            ),
            part_number:
              String(line.part_number || '').trim() ||
              String(product?.part_number || '').trim() ||
              '',
          };
        })
      : [emptyLine()];
    const mappedLines = applyParsedPackingWeights(mappedLinesRaw, parsedData);
    const firstChallan = mappedLines.find((l) => String(l.challan_number || '').trim())?.challan_number;
    const headerReferenceDate =
      parsedData.reference_date ||
      parsedData.items?.find((line) => line.reference_date)?.reference_date;
    const headerLrDate =
      parsedData.lr_date || parsedData.items?.find((line) => line.lr_date)?.lr_date;

    reset({
      ...getValues(),
      vendor_id: (parsedData.vendor_id && String(parsedData.vendor_id)) || getValues('vendor_id'),
      supplier_document_number:
        firstChallan ||
        parsedData.reference_document_number ||
        parsedData.invoice_number ||
        getValues('supplier_document_number'),
      supplier_document_date: dateStr,
      reference_date: headerReferenceDate
        ? toDateInput(headerReferenceDate)
        : getValues('reference_date'),
      transporter_name: parsedData.transporter_name || getValues('transporter_name'),
      vehicle_number: parsedData.vehicle_number || getValues('vehicle_number'),
      lr_number: parsedData.lr_number || getValues('lr_number'),
      lr_date: headerLrDate ? toDateInput(headerLrDate) : getValues('lr_date'),
      po_number: parsedData.po_number || getValues('po_number'),
      remarks:
        [parsedData.destination, parsedData.remarks]
          .filter((t) => t && !/^DC\d+/i.test(String(t).trim()))
          .join(' — ') || getValues('remarks'),
      lines: mappedLines,
    });
    replace(mappedLines);
    mappedLines.forEach((_, idx) => {
      setValue(`lines.${idx}.short_quantity`, '', { shouldDirty: false });
    });
  }, [parsedData, productOptions, reset, replace, getValues, setValue]);

  useEffect(() => {
    if (!parsedData?.items?.length || !productOptions.length) return;
    const allowed = new Set(productOptions.map((p) => String(p.id)));
    parsedData.items.forEach((src, index) => {
      const current = getValues(`lines.${index}.product_id`);
      if (current && allowed.has(String(current))) return;
      const productId = matchProduct(src, productOptions);
      if (!productId) return;
      setValue(`lines.${index}.product_id`, productId, { shouldDirty: true });
      const product = productOptions.find((p) => String(p.id) === String(productId));
      if (product?.net_weight != null && product.net_weight !== '') {
        setValue(`lines.${index}.per_ring_weight`, product.net_weight);
      }
      if (product?.packing_ratio && !String(getValues(`lines.${index}.packing_ratio`) || '').trim()) {
        setValue(`lines.${index}.packing_ratio`, product.packing_ratio);
      }
      if (product?.unit_rate) setValue(`lines.${index}.unit_rate`, product.unit_rate);
      setValue(`lines.${index}.short_quantity`, '', { shouldDirty: false });
    });
  }, [parsedData, productOptions, getValues, setValue]);

  const recalcLineQty = (index, shortOverride) => {
    queueMicrotask(() => {
      const line = getValues(`lines.${index}`);
      const packed = packingQty(line);
      if (packed > 0) {
        const short =
          shortOverride !== undefined ? parseShortQty(shortOverride) : parseShortQty(line.short_quantity);
        setValue(`lines.${index}.quantity`, Math.max(0, packed - short), { shouldDirty: true });
      }
    });
  };

  const lineTotals = (watchedLines || []).map((row) => {
    const qty = lineNetQty(row);
    const rate = Number(row?.unit_rate) || 0;
    const gstPct = Number(row?.gst_percent) || 0;
    const taxable = qty * rate;
    const gst = taxable * (gstPct / 100);
    const ringWt = Number(row?.per_ring_weight) || 0;
    const pack = Number(row?.packing_weight) || 0;
    const gross = lineGrossWeight(qty, ringWt);
    const weightTotal = lineTotalWeight(qty, ringWt, pack);
    return {
      qty,
      taxable,
      gst,
      total: taxable + gst,
      gross,
      linePacking: pack,
      weightTotal,
    };
  });
  const summary = lineTotals.reduce(
    (acc, line) => {
      acc.qty += line.qty;
      acc.taxable += line.taxable;
      acc.gst += line.gst;
      acc.grand += line.total;
      acc.grossWeight += line.gross;
      acc.linePacking += line.linePacking;
      acc.totalWeight += line.weightTotal;
      return acc;
    },
    { qty: 0, taxable: 0, gst: 0, grand: 0, grossWeight: 0, linePacking: 0, totalWeight: 0 }
  );

  const onProductChange = (index, productId) => {
    setValue(`lines.${index}.product_id`, productId, { shouldDirty: true });
    const option = productOptions.find((p) => String(p.id) === String(productId));
    const ringWt = option?.net_weight;
    if (ringWt != null && ringWt !== '') setValue(`lines.${index}.per_ring_weight`, ringWt);
    if (option?.unit_rate) setValue(`lines.${index}.unit_rate`, option.unit_rate);
    setValue(`lines.${index}.short_quantity`, '', { shouldDirty: false });
    if (option?.packing_ratio && !String(getValues(`lines.${index}.packing_ratio`) || '').trim()) {
      setValue(`lines.${index}.packing_ratio`, option.packing_ratio);
    }
    if (option?.part_number && !String(getValues(`lines.${index}.part_number`) || '').trim()) {
      setValue(`lines.${index}.part_number`, option.part_number);
    }
  };

  const openRemarkModal = (index, fromYesSelect = false) => {
    const remarks = getValues(`lines.${index}.remarks`) || '';
    const hasRemark = getValues(`lines.${index}.has_remark`) || 'no';
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
      setValue(`lines.${remarkModalIndex}.has_remark`, has_remark, { shouldDirty: true });
      setValue(`lines.${remarkModalIndex}.remarks`, remarks, { shouldDirty: true });
    }
    setRemarkModalIndex(null);
  };

  const saveRemarkModal = () => {
    if (remarkModalIndex == null) return;
    const text = remarkDraft.trim();
    if (!text) {
      window.alert('Please enter remark text.');
      return;
    }
    setValue(`lines.${remarkModalIndex}.remarks`, text, { shouldDirty: true });
    setValue(`lines.${remarkModalIndex}.has_remark`, 'yes', { shouldDirty: true });
    setRemarkModalIndex(null);
  };

  const onSubmit = async (form) => {
    try {
      const workflow = form.workflow || (workflowMaster === 'BOTH' ? '' : workflowMaster);
      const filled = form.lines.filter((line) => {
        const qty = packingQty(line) || Number(line.quantity || 0);
        return line.product_id && qty > 0;
      });
      if (!filled.length) {
        window.alert('Add at least one product with quantity.');
        return;
      }
      const headerRef =
        String(form.supplier_document_number || '').trim() ||
        String(filled[0].challan_number || '').trim() ||
        String(filled[0].reference_number || '').trim();
      if (!headerRef) {
        window.alert('Enter a reference / challan number on the header or on at least one line.');
        return;
      }
      const doc = await mutateAsync({
        warehouse_id: form.warehouse_id,
        vendor_id: form.vendor_id,
        workflow: workflow || undefined,
        supplier_document_number: headerRef,
        supplier_document_date: form.supplier_document_date || null,
        reference_date: form.reference_date || null,
        received_date: form.received_date || null,
        transporter_name: form.transporter_name || null,
        vehicle_number: form.vehicle_number || null,
        lr_number: form.lr_number || null,
        lr_date: form.lr_date || null,
        po_number: form.po_number || null,
        packing_weight: filled.reduce((sum, line) => sum + Number(line.packing_weight || 0), 0),
        remarks: form.remarks || null,
        lines: filled.map((line) => {
          const product = productOptions.find((p) => String(p.id) === String(line.product_id));
          const catalog = (Array.isArray(supplierTypes) ? supplierTypes : []).find(
            (t) => String(t.product_id) === String(line.product_id)
          );
          const quantity = lineNetQty(line);
          return {
            product_id: line.product_id,
            uom_id: product?.uom_id || catalog?.uom_id,
            heat_number: String(line.heat_number || '').trim() || undefined,
            pallet_count: Number(line.pallet_count || 0),
            qty_per_pallet: Number(line.qty_per_pallet || 0),
            box_count: Number(line.box_count || 0),
            qty_per_box: Number(line.qty_per_box || 0),
            quantity,
            short_quantity:
              line.short_quantity === '' || line.short_quantity == null
                ? undefined
                : Number(line.short_quantity),
            unit_rate: Number(line.unit_rate || 0),
            per_ring_weight: line.per_ring_weight === '' ? undefined : Number(line.per_ring_weight),
            packing_weight: Number(line.packing_weight || 0),
            source_document_number: String(line.challan_number || '').trim() || undefined,
            source_document_date: form.supplier_document_date || undefined,
            reference_number: String(line.reference_number || '').trim() || undefined,
            part_number: String(line.part_number || '').trim() || undefined,
            transporter_name: form.transporter_name || undefined,
            packing_detail: buildPackingDetail(line),
            remarks: line.has_remark === 'yes' && String(line.remarks || '').trim()
              ? String(line.remarks).trim()
              : undefined,
          };
        }),
      });
      navigate(doc?.id ? `/rings/inward/${doc.id}` : '/rings/inward');
    } catch (err) {
      window.alert(err.response?.data?.message || err.message || 'Failed to post inward');
    }
  };

  return (
    <InwardDocumentUpload
      multiple
      onParsed={setParsedData}
      render={({ trigger, feedback }) => (
    <div className="space-y-6">
      <PageHeader
        title="New Inward Transaction"
        description="Record a new receipt of materials into the warehouse."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Inward', to: '/rings/inward' },
          { label: 'New Inward' },
        ]}
        actions={trigger}
      />
      {feedback}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <Card.Header className="py-3">
            <h3 className="text-base font-medium">Header Information</h3>
          </Card.Header>
          <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-3 py-3">
            <div className="space-y-1">
              <label htmlFor="warehouse_id" className="text-xs font-medium text-gray-600">Warehouse</label>
              <select id="warehouse_id" {...register('warehouse_id', { required: true })} className={lineSelectClass}>
                <option value="">Select Warehouse</option>
                {warehouses.map((wh) => (
                  <option key={wh.id} value={wh.id}>{wh.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label htmlFor="vendor_id" className="text-xs font-medium text-gray-600">Supplier</label>
              <select id="vendor_id" {...register('vendor_id', { required: true })} className={lineSelectClass}>
                <option value="">Select Supplier</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
            <Input
              label="Challan Date"
              type="date"
              className="py-1.5 text-sm"
              isRequired
              {...register('supplier_document_date')}
            />
            <Input
              label="Reference Date"
              type="date"
              className="py-1.5 text-sm"
              {...register('reference_date')}
            />
            {workflowMaster === 'BOTH' && (
              <div className="space-y-1">
                <label htmlFor="workflow" className="text-xs font-medium text-gray-600">Reference Type</label>
                <select id="workflow" className={lineSelectClass} {...register('workflow', { required: true })}>
                  <option value="">Select</option>
                  <option value="JOB_WORK">Job Work</option>
                  <option value="DIRECT_INVOICE">Direct Invoice</option>
                </select>
              </div>
            )}
            <Input label="Transporter" className="py-1.5 text-sm" {...register('transporter_name')} />
            <Input label="Vehicle" className="py-1.5 text-sm" {...register('vehicle_number')} />
            <Input label="LR / GR" className="py-1.5 text-sm" {...register('lr_number')} />
            <Input label="LR Date" type="date" className="py-1.5 text-sm" {...register('lr_date')} />
            <Input label="Received Date" type="date" className="py-1.5 text-sm" {...register('received_date')} />
            <Input label="PO Number" className="py-1.5 text-sm" {...register('po_number')} />
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
            <Button type="button" variant="secondary" size="sm" onClick={() => append(emptyLine())}>
              <Plus className="w-4 h-4 mr-1" /> Add Item
            </Button>
          </Card.Header>
          <Card.Body className="py-2 px-3">
            <div className="overflow-x-auto -mx-1 px-1">
              <div className="min-w-[125rem] px-1">
                <table className="w-full border-separate border-spacing-y-1.5">
                  <colgroup>
                    <col className="w-[10.5rem]" />
                    <col className="w-[5.5rem]" />
                    <col className="w-[7.75rem]" />
                    <col className="w-[4.5rem]" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th className={`${thBase} w-[10.5rem]`}>Product</th>
                      <th className={`${thBase} w-[5.5rem]`}>HSN</th>
                      <th className={`${thBase} ${challanColClass}`}>Challan No</th>
                      <th className={`${thBase} w-[4.5rem]`}>Ref No</th>
                      <th className={thBase}>Ratio</th>
                      <th className={thBase}>Pallets</th>
                      <th className={thBase}>Qty / Pallet</th>
                      <th className={thBase}>Boxes</th>
                      <th className={thBase}>Qty / Box</th>
                      <th className={thBase}>Short Qty</th>
                      <th className={thBase}>Qty</th>
                      <th className={`${thBase} min-w-[8.5rem] w-36`}>Heat No.</th>
                      <th className={`${thBase} w-[6.5rem]`}>Part No</th>
                      <th className={thBase}>UOM</th>
                      <th className={thBase}>Rate</th>
                      <th className={thBase}>GST%</th>
                      <th className={thBase}>Taxable ₹</th>
                      <th className={thBase}>Ring Wt</th>
                      <th className={thBase}>Packing Wt</th>
                      <th className={thBase}>Gross Wt</th>
                      <th className={thBase}>Total Wt</th>
                      <th className={thBase}>Total ₹</th>
                      <th className={thBase}>
                        <div className="inline-flex items-center justify-center gap-0.5 mx-auto">
                          <span>Remark</span>
                          <span className={remarkEditSlotClass} aria-hidden />
                        </div>
                      </th>
                      <th className={thBase} aria-hidden />
                    </tr>
                  </thead>
                  <tbody>
                    {fields.map((field, index) => {
                      const product = productOptions.find(
                        (p) => String(p.id) === String(watchedLines[index]?.product_id)
                      );
                      const uom = (uomsData || []).find((u) => String(u.id) === String(product?.uom_id));
                      const lineHasRemark = watchedLines[index]?.has_remark === 'yes';
                      const wt = lineTotals[index];
                      return (
                        <tr key={field.id} className={itemRowTrClass}>
                          <td className={`${tdBase} w-[10.5rem] max-w-[10.5rem]`}>
                            <input
                              type="hidden"
                              {...register(`lines.${index}.product_id`, { required: true })}
                            />
                            <SearchableSelect
                              value={watchedLines[index]?.product_id || ''}
                              options={productOptions}
                              getOptionLabel={productLabel}
                              getOptionValue={(p) => p.id}
                              disabled={!vendorId}
                              className={lineProductSelectClass}
                              placeholder={
                                !vendorId
                                  ? 'Select supplier first'
                                  : productOptions.length
                                    ? 'Select product'
                                    : 'No products for this supplier'
                              }
                              searchPlaceholder="Search SKU..."
                              onChange={(productId) => onProductChange(index, productId)}
                            />
                          </td>
                          <td
                            className={`${tdBase} text-center text-[11px] font-mono text-gray-600 w-[5.5rem]`}
                            title="From product master (PDF upload can update HSN on the product)"
                          >
                            {formatHsnDisplay(product?.hsn_code)}
                          </td>
                          <td className={`${tdBase} ${challanColClass}`}>
                            <input
                              type="text"
                              autoComplete="off"
                              placeholder="DC252600257"
                              title={watchedLines[index]?.challan_number || ''}
                              className={challanInputClass}
                              {...register(`lines.${index}.challan_number`)}
                            />
                          </td>
                          <td className={`${tdBase} w-[4.5rem] max-w-[4.5rem]`}>
                            <input
                              type="text"
                              autoComplete="off"
                              placeholder="0257"
                              maxLength={8}
                              className={`${numInputClass} font-mono text-xs text-center`}
                              {...register(`lines.${index}.reference_number`)}
                            />
                          </td>
                          <td className={tdBase}>
                            <input
                              type="text"
                              autoComplete="off"
                              placeholder="2+1+1"
                              className={numInputClass}
                              {...register(`lines.${index}.packing_ratio`)}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="numeric"
                              className={numInputRightClass}
                              {...register(`lines.${index}.pallet_count`, {
                                onChange: () => recalcLineQty(index),
                              })}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              {...register(`lines.${index}.qty_per_pallet`, {
                                onChange: () => recalcLineQty(index),
                              })}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="numeric"
                              className={numInputRightClass}
                              {...register(`lines.${index}.box_count`, {
                                onChange: () => recalcLineQty(index),
                              })}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              {...register(`lines.${index}.qty_per_box`, {
                                onChange: () => recalcLineQty(index),
                              })}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              key={`${field.id}-short-qty`}
                              type="text"
                              inputMode="decimal"
                              placeholder="—"
                              autoComplete="off"
                              className={numInputRightClass}
                              {...register(`lines.${index}.short_quantity`, {
                                setValueAs: (v) => (v === '' || v == null ? '' : v),
                                onChange: (e) => recalcLineQty(index, e.target.value),
                              })}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="decimal"
                              readOnly={packingQty(watchedLines[index] || {}) > 0}
                              title={
                                packingQty(watchedLines[index] || {}) > 0
                                  ? 'Qty = (boxes × qty/box) − short qty'
                                  : undefined
                              }
                              className={`${numInputRightClass}${
                                packingQty(watchedLines[index] || {}) > 0 ? ' bg-gray-50' : ''
                              }`}
                              {...register(`lines.${index}.quantity`)}
                            />
                          </td>
                          <td className={`${tdBase} min-w-[8.5rem] w-36`}>
                            <input
                              type="text"
                              autoComplete="off"
                              placeholder="Optional"
                              className={`${numInputClass} px-2 min-w-[8rem]`}
                              {...register(`lines.${index}.heat_number`)}
                            />
                          </td>
                          <td className={`${tdBase} w-[6.5rem] max-w-[6.5rem]`}>
                            <input
                              type="text"
                              autoComplete="off"
                              placeholder="90030370"
                              title="Supplier invoice Part No (Manu Yantralaya, etc.)"
                              className={`${numInputClass} font-mono text-[11px] px-1`}
                              {...register(`lines.${index}.part_number`)}
                            />
                          </td>
                          <td className={`${tdBase} text-center text-xs text-gray-600`}>
                            {uom?.code || '—'}
                          </td>
                          <td className={tdR}>
                            <input
                              key={`${field.id}-unit-rate`}
                              type="text"
                              inputMode="decimal"
                              placeholder="0"
                              autoComplete="off"
                              className={numInputRightClass}
                              {...register(`lines.${index}.unit_rate`)}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              readOnly
                              {...register(`lines.${index}.gst_percent`)}
                            />
                          </td>
                          <td className={`${tdAmount} text-xs text-gray-600`}>
                            {formatAmount(lineTotals[index]?.taxable ?? 0)}
                          </td>
                          <td className={tdR}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              {...register(`lines.${index}.per_ring_weight`)}
                            />
                          </td>
                          <td className={tdR}>
                            <input
                              key={`${field.id}-packing-wt`}
                              type="text"
                              inputMode="decimal"
                              placeholder="0"
                              autoComplete="off"
                              className={numInputRightClass}
                              {...register(`lines.${index}.packing_weight`)}
                            />
                          </td>
                          <td className={`${tdAmount} text-xs font-medium text-gray-800`}>
                            {wt?.qty ? formatWt(wt.gross) : '—'}
                          </td>
                          <td className={`${tdAmount} text-xs font-semibold text-gray-900`}>
                            {wt?.qty ? formatWt(wt.weightTotal) : '—'}
                          </td>
                          <td className={`${tdAmount} text-sm font-medium text-gray-900`}>
                            {formatAmount(lineTotals[index]?.total ?? 0)}
                          </td>
                          <td className={tdBase}>
                            <input type="hidden" {...register(`lines.${index}.remarks`)} />
                            <div className="flex items-center gap-0.5">
                              <select
                                className={`${lineSelectClass} flex-1 min-w-0 py-1 pl-1.5 pr-1 text-xs`}
                                title={
                                  lineHasRemark && watchedLines[index]?.remarks?.trim()
                                    ? watchedLines[index].remarks
                                    : undefined
                                }
                                {...register(`lines.${index}.has_remark`, {
                                  onChange: (e) => {
                                    if (e.target.value === 'yes') {
                                      openRemarkModal(index, true);
                                    } else {
                                      setValue(`lines.${index}.remarks`, '', { shouldDirty: true });
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
                                  title={watchedLines[index]?.remarks?.trim() || 'Edit remark'}
                                  aria-label="Edit remark"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                              ) : (
                                <span className={remarkEditSlotClass} aria-hidden />
                              )}
                            </div>
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
                <div className="flex justify-between sm:justify-end gap-4 text-xs text-gray-500 pt-1">
                  <span>Gross weight (kg)</span>
                  <span className="tabular-nums">{formatWt(summary.grossWeight)}</span>
                </div>
                <div className="flex justify-between sm:justify-end gap-4 text-xs font-medium text-gray-700">
                  <span>Total weight (kg)</span>
                  <span className="tabular-nums">{formatWt(summary.totalWeight)}</span>
                </div>
              </div>
            </div>
          </Card.Body>
          <Card.Footer className="flex justify-end gap-2 py-3">
            <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/rings/inward')}>
              Cancel
            </Button>
            <Button type="submit" size="sm" isLoading={isPending}>
              Post Inward
            </Button>
          </Card.Footer>
        </Card>
      </form>
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
    </div>
      )}
    />
  );
};

export default RingsInwardCreatePage;
