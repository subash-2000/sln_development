import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import {
  isBulkInwardLine,
  isPalletSupplier,
  isPalletSupplierBlob,
  normalizeParsedItemsPacking,
} from '../utils/packaging';

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

const buildPackingDetail = (line, isPallet = false) => {
  const ratio = String(line?.packing_ratio || '').trim();
  const boxes = Number(line?.box_count || 0);
  const perBox = Number(line?.qty_per_box || 0);
  const pallets = Number(line?.pallet_count || 0);
  const perPallet = Number(line?.qty_per_pallet || 0);
  const qty = packingQty(line) || Number(line?.quantity || 0);
  if (pallets && perPallet) {
    return `${perPallet}x${pallets} = ${qty}${ratio ? ` (${ratio})` : ''}`.slice(0, 100);
  }
  if (boxes && perBox) {
    return `${perBox}x${boxes} = ${qty}${ratio ? ` (${ratio})` : ''}`.slice(0, 100);
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
const qtyTotalTdClass = `${tdR} min-w-[7rem] w-[7rem]`;
const qtyTotalInputClass = `${numInputRightClass} min-w-[6.5rem] font-medium`;
const rateInputTdClass = `${tdR} min-w-[5.5rem] w-[5.5rem]`;
const wtInputTdClass = `${tdR} min-w-[6rem] w-[6rem]`;
const amountDisplayTdClass = `${tdAmount} min-w-[6.5rem]`;
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

const inferRingSkuFromLine = (line) => {
  const blob = `${line?.sku_guess || ''} ${line?.description || ''}`.toUpperCase();
  const compact = blob.replace(/\s+/g, '');
  const sizeMatch = blob.match(/\b(\d{3,5})\b/) || compact.match(/(?:OM|IM)(\d{3,5})/);
  if (!sizeMatch) return '';
  const size = sizeMatch[1];
  const isOuter =
    /\bOR\b|ORPOYO|OUTER|\d{3,5}OR\b/.test(blob) ||
    compact.startsWith('OM') ||
    compact.includes(`OM${size}`);
  const isInner =
    /\bIR\b|IRPOYO|INNER|\d{3,5}IR\b/.test(blob) ||
    compact.startsWith('IM') ||
    compact.includes(`IM${size}`);
  if (isOuter && !isInner) return `OM${size}`;
  if (isInner && !isOuter) return `IM${size}`;
  return '';
};

const normalizeSkuToken = (value) => String(value || '').toUpperCase().replace(/\s+/g, '');
const normalizeRatio = (value) => String(value || '').replace(/\s+/g, '').toUpperCase();

/** Build SKU tokens to match master rows like OM6005, IM6005, "6005 OR", "6005 IR". */
const buildSkuMatchCandidates = (line) => {
  const tokens = [];
  const seen = new Set();
  const add = (raw) => {
    const t = normalizeSkuToken(raw);
    if (t && !seen.has(t)) {
      seen.add(t);
      tokens.push(t);
    }
  };
  const inferred = inferRingSkuFromLine(line);
  add(inferred);
  add(line?.sku_guess);
  const blob = `${line?.sku_guess || ''} ${line?.description || ''}`.toUpperCase();
  const sizeMatch = blob.match(/\b(\d{3,5})\b/);
  if (sizeMatch) {
    const size = sizeMatch[1];
    if (/\bOR\b|ORPOYO|OUTER|\d{3,5}OR\b/.test(blob) && !/\bIR\b|IRPOYO|INNER|\d{3,5}IR\b/.test(blob)) {
      add(`OM${size}`);
      add(`${size}OR`);
    }
    if (/\bIR\b|IRPOYO|INNER|\d{3,5}IR\b/.test(blob) && !/\bOR\b|ORPOYO|OUTER|\d{3,5}OR\b/.test(blob)) {
      add(`IM${size}`);
      add(`${size}IR`);
    }
  }
  if (inferred?.startsWith('OM')) add(`${inferred.slice(2)}OR`);
  if (inferred?.startsWith('IM')) add(`${inferred.slice(2)}IR`);
  return tokens;
};

const productSkuMatchesCandidate = (productSku, candidate) => {
  const ps = normalizeSkuToken(productSku);
  const c = normalizeSkuToken(candidate);
  if (!ps || !c) return false;
  if (ps === c) return true;
  // Avoid matching bare size "6005" to every 6005* SKU (picks wrong ring type).
  if (/^\d{3,5}$/.test(c)) return false;
  if (/^\d{3,5}(OR|IR)$/.test(c) && (ps.startsWith('OM') || ps.startsWith('IM'))) return false;
  if (ps.startsWith(c) || c.startsWith(ps)) return true;
  return false;
};

const matchCanonicalRing = (line, products) => {
  const inferred = inferRingSkuFromLine(line);
  if (inferred) {
    const hit = products.find((p) => normalizeSkuToken(p.sku) === inferred);
    if (hit) return String(hit.id);
  }
  const sizeMatch = `${line?.sku_guess || ''} ${line?.description || ''}`.match(/\b(\d{3,5})\b/);
  const size = sizeMatch ? sizeMatch[1] : '';
  const ratio = normalizeRatio(line?.packing_ratio);
  if (size && ratio) {
    const hits = products.filter((p) => {
      const sku = normalizeSkuToken(p.sku);
      const pr = normalizeRatio(p.packing_ratio);
      return (
        (sku === `OM${size}` || sku === `IM${size}`) &&
        pr &&
        (pr === ratio || pr.startsWith(ratio) || ratio.startsWith(pr))
      );
    });
    if (hits.length === 1) return String(hits[0].id);
  }
  return '';
};

const matchProduct = (line, products) => {
  if (!products?.length) return '';

  const canonicalId = matchCanonicalRing(line, products);
  if (canonicalId) return canonicalId;

  const guess = `${line?.sku_guess || ''} ${line?.description || ''}`.toUpperCase();
  const compact = guess.replace(/\s+/g, '');
  const prefersOm = /\bOR\b|ORPOYO|OUTER|\d{3,5}OR\b/.test(guess) || compact.startsWith('OM');
  const prefersIm = /\bIR\b|IRPOYO|INNER|\d{3,5}IR\b/.test(guess) || compact.startsWith('IM');
  const ringTyped = prefersOm || prefersIm;

  const skuCandidates = buildSkuMatchCandidates(line);
  for (const candidate of skuCandidates) {
    const exactSku = products.find((p) => productSkuMatchesCandidate(p.sku, candidate));
    if (exactSku) return String(exactSku.id);
  }

  if (line?.product_id) {
    const byId = products.find((p) => String(p.id) === String(line.product_id));
    const sku = normalizeSkuToken(byId?.sku);
    const isAlias = /^\d{3,5}(OR|IR)$/.test(sku);
    if (byId && !isAlias) return String(byId.id);
  }

  if (!guess.trim()) return '';
  const digits = [...new Set(guess.match(/\b\d{3,5}\b/g) || [])];

  const sorted = [...products].sort(
    (a, b) => normalizeSkuToken(b.sku).length - normalizeSkuToken(a.sku).length,
  );
  const exact = sorted.find((p) => {
    const sku = normalizeSkuToken(p.sku);
    const name = String(p.name || '').toUpperCase().trim();
    if (/^\d{3,5}(OR|IR)$/.test(sku) && products.some((x) => /^(OM|IM)\d/.test(normalizeSkuToken(x.sku)))) {
      return false;
    }
    if (sku.length >= 5 && guess.includes(sku)) return true;
    if (name.length >= 6 && guess.includes(name)) return true;
    return false;
  });
  if (exact) return String(exact.id);

  let best = null;
  let bestScore = 0;
  const lineRatio = normalizeRatio(line?.packing_ratio);
  products.forEach((p) => {
    const sku = normalizeSkuToken(p.sku);
    const name = String(p.name || '').toUpperCase();
    const blob = `${sku}${name}`.replace(/\s+/g, '');
    let score = 0;
    digits.forEach((d) => {
      if (blob.includes(d)) score += 8;
    });
    if (prefersOm && sku.startsWith('OM')) score += 36;
    if (prefersIm && sku.startsWith('IM')) score += 36;
    if (prefersOm && (sku.endsWith('OR') || name.includes(' OR'))) score += 12;
    if (prefersIm && (sku.endsWith('IR') || name.includes(' IR'))) score += 12;
    if (prefersOm && (sku.endsWith('IR') || name.includes(' IR'))) score -= 40;
    if (prefersIm && (sku.endsWith('OR') || name.includes(' OR'))) score -= 40;
    const pr = normalizeRatio(p.packing_ratio);
    if (lineRatio && pr && (pr === lineRatio || pr.startsWith(lineRatio) || lineRatio.startsWith(pr))) {
      score += 18;
    }
    if (score > bestScore) {
      bestScore = score;
      best = p;
    }
  });
  const minScore = ringTyped ? 20 : 12;
  return bestScore >= minScore ? String(best.id) : '';
};

const productLabel = (product) => {
  const sku = String(product?.sku || '').trim();
  const name = String(product?.name || '').trim();
  if (!name || !sku || name.toUpperCase() === sku.toUpperCase()) return sku || name || 'Product';
  return `${sku} — ${name}`;
};

const resolveDocIsPallet = (parsedData, vendors, vendorId) => {
  if (!parsedData) return false;
  const effectiveVendorId = vendorId || parsedData.vendor_id;
  const targetVendor =
    vendors.find((v) => String(v.id) === String(parsedData.vendor_id)) ||
    vendors.find((v) => String(v.id) === String(effectiveVendorId)) ||
    vendors.find(
      (v) =>
        (v.code && v.code === parsedData.supplier_key) ||
        (v.name &&
          parsedData.supplier_name &&
          v.name.toLowerCase() === parsedData.supplier_name.toLowerCase())
    );
  const formVendor = vendors.find((v) => String(v.id) === String(effectiveVendorId));
  return (
    isPalletSupplier(formVendor) ||
    isPalletSupplier(targetVendor) ||
    isPalletSupplierBlob(`${parsedData.supplier_key || ''} ${parsedData.supplier_name || ''}`)
  );
};

/** Stable pallet vs box for one PDF apply (avoids flip-flop when vendor list re-fetches). */
const resolveUsePallet = (parsedData, vendors, vendorId) => {
  if (resolveDocIsPallet(parsedData, vendors, vendorId)) return true;
  const id = vendorId || parsedData?.vendor_id;
  if (!id || !vendors.length) return false;
  const v = vendors.find((x) => String(x.id) === String(id));
  return isPalletSupplier(v);
};

const mapParsedLinePacking = (line, usePallet) => {
  const qty = Number(line.quantity ?? 0);
  if (isBulkInwardLine(line)) {
    return {
      pallet_count: 0,
      qty_per_pallet: 0,
      box_count: 0,
      qty_per_box: 0,
    };
  }
  const rawPkg = Number(line.package_count || 0);
  const pCount = Number(line.pallet_count || 0);
  const pQty = Number(line.qty_per_pallet || 0);
  const bCount = Number(line.box_count || 0);
  const bQty = Number(line.qty_per_box || line.box_quantity || 0);

  if (usePallet) {
    const finalPallets = pCount || bCount || rawPkg;
    let finalQtyPerPallet = pQty || bQty;
    if (!finalQtyPerPallet && finalPallets > 0 && qty > 0) {
      finalQtyPerPallet = qty / finalPallets;
    }
    return {
      pallet_count: finalPallets,
      qty_per_pallet: finalQtyPerPallet,
      box_count: 0,
      qty_per_box: 0,
    };
  }

  const finalBoxes = bCount || pCount || rawPkg;
  let finalQtyPerBox = bQty || pQty;
  if (!finalQtyPerBox && finalBoxes > 0 && qty > 0) {
    finalQtyPerBox = qty / finalBoxes;
  }
  return {
    pallet_count: 0,
    qty_per_pallet: 0,
    box_count: finalBoxes,
    qty_per_box: finalQtyPerBox,
  };
};

const RingsInwardCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync, isPending } = useCreateRingsInward();
  const [parsedData, setParsedData] = useState(null);
  const lastParseKeyRef = useRef(null);
  const applyingParsedRef = useRef(false);
  const [remarkModalIndex, setRemarkModalIndex] = useState(null);
  const [remarkDraft, setRemarkDraft] = useState('');
  const remarkRevertRef = useRef({ has_remark: 'no', remarks: '' });
  const { data: warehousesData } = useWarehouses();
  const { data: vendorsData } = useVendors({ page_size: 200, status: 'ACTIVE' });
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
  const vendor = useMemo(
    () => vendors.find((v) => String(v.id) === String(vendorId)),
    [vendors, vendorId]
  );
  const isPalletMode = useMemo(() => isPalletSupplier(vendor), [vendor]);
  const workflowMaster = vendor?.invoice_workflow || 'STANDARD';
  const isDirect = (watch('workflow') || workflowMaster) === 'DIRECT_INVOICE';

  const prevVendorRef = useRef(vendorId);
  useEffect(() => {
    if (applyingParsedRef.current) {
      prevVendorRef.current = vendorId;
      return;
    }
    if (prevVendorRef.current !== vendorId) {
      const prevV = prevVendorRef.current
        ? vendors.find((v) => String(v.id) === String(prevVendorRef.current))
        : null;
      const wasPallet = isPalletSupplier(prevV);
      const nowPallet = isPalletSupplier(vendor);
      if (nowPallet && !wasPallet) {
        const curLines = getValues('lines') || [];
        curLines.forEach((l, idx) => {
          const bCount = Number(l?.box_count || 0);
          const bQty = Number(l?.qty_per_box || 0);
          if (bCount > 0 || bQty > 0) {
            setValue(`lines.${idx}.pallet_count`, bCount, { shouldDirty: true });
            setValue(`lines.${idx}.qty_per_pallet`, bQty, { shouldDirty: true });
            setValue(`lines.${idx}.box_count`, 0, { shouldDirty: true });
            setValue(`lines.${idx}.qty_per_box`, 0, { shouldDirty: true });
          }
        });
      } else if (!nowPallet && wasPallet) {
        const curLines = getValues('lines') || [];
        curLines.forEach((l, idx) => {
          const pCount = Number(l?.pallet_count || 0);
          const pQty = Number(l?.qty_per_pallet || 0);
          if (pCount > 0 || pQty > 0) {
            setValue(`lines.${idx}.box_count`, pCount, { shouldDirty: true });
            setValue(`lines.${idx}.qty_per_box`, pQty, { shouldDirty: true });
            setValue(`lines.${idx}.pallet_count`, 0, { shouldDirty: true });
            setValue(`lines.${idx}.qty_per_pallet`, 0, { shouldDirty: true });
          }
        });
      }
    }
    prevVendorRef.current = vendorId;
  }, [vendorId, vendor, vendors, getValues, setValue]);

  const productOptions = useMemo(() => {
    if (!vendorId) return [];
    const types = Array.isArray(supplierTypes) ? supplierTypes : [];
    const seen = new Set();
    const list = [];
    types.forEach((t) => {
      const id = String(t.product_id);
      if (id && !seen.has(id)) {
        seen.add(id);
        list.push({
          id: t.product_id,
          sku: t.product_sku,
          name: t.product_name || t.product_sku,
          uom_id: t.uom_id,
          net_weight: t.per_ring_weight,
          unit_rate: t.unit_rate,
          packing_ratio: t.packing_ratio,
        });
      }
    });
    (catalogData?.items || []).forEach((c) => {
      const id = String(c.id);
      if (id && !seen.has(id)) {
        seen.add(id);
        list.push({
          id: c.id,
          sku: c.sku,
          name: c.name || c.sku,
          uom_id: c.uom_id,
          net_weight: c.net_weight,
          unit_rate: c.unit_rate || c.standard_cost,
          packing_ratio: c.packing_ratio,
        });
      }
    });
    return list.sort((a, b) =>
      (a.sku || a.name || '').localeCompare(b.sku || b.name || '', undefined, { numeric: true, sensitivity: 'base' })
    );
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
        const isFromParsed = parsedData?.items?.some((it) => String(it.product_id) === String(line.product_id));
        if (isFromParsed) return;
        setValue(`lines.${index}.product_id`, '');
        setValue(`lines.${index}.per_ring_weight`, '');
      }
    });
  }, [vendorId, typesFetched, productOptions, getValues, setValue]);

  useEffect(() => {
    if (!parsedData) return;
    const effectiveVendorId =
      vendorId || getValues('vendor_id') || parsedData.vendor_id || '';
    const parseKey = JSON.stringify({
      source: parsedData.source_files,
      items: parsedData.items,
      ref: parsedData.reference_document_number || parsedData.invoice_number,
      vendorId: effectiveVendorId,
      vendorCatalogSize: vendors.length,
    });
    if (lastParseKeyRef.current === parseKey) return;
    lastParseKeyRef.current = parseKey;

    const usePallet = resolveUsePallet(parsedData, vendors, effectiveVendorId);
    const sourceItems = normalizeParsedItemsPacking(parsedData.items || [], usePallet);

    const dateStr = parsedData.transaction_date
      ? String(parsedData.transaction_date).slice(0, 10)
      : getValues('supplier_document_date');
    const mappedLinesRaw = sourceItems.length
      ? sourceItems.map((line) => {
          const productId = matchProduct(line, productOptions);
          const product = productOptions.find((p) => String(p.id) === String(productId));
          const qty = Number(line.quantity ?? 0);
          const packing = mapParsedLinePacking(line, usePallet);

          const calculatedQty =
            qty ||
            (packing.pallet_count && packing.qty_per_pallet
              ? packing.pallet_count * packing.qty_per_pallet
              : packing.box_count && packing.qty_per_box
                ? packing.box_count * packing.qty_per_box
                : 0);

          return {
            ...emptyLine(),
            product_id: productId,
            heat_number: line.lot_number || line.heat_number || '',
            packing_ratio: line.packing_ratio || product?.packing_ratio || '',
            has_remark: line.remarks ? 'yes' : 'no',
            remarks: line.remarks || '',
            ...packing,
            quantity: calculatedQty,
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

    applyingParsedRef.current = true;
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
    queueMicrotask(() => {
      applyingParsedRef.current = false;
    });
  }, [parsedData, vendors, vendorId, productOptions, reset, replace, getValues, setValue]);

  useEffect(() => {
    if (!parsedData?.items?.length || !productOptions.length) return;
    parsedData.items.forEach((src, index) => {
      const productId = matchProduct(src, productOptions);
      if (!productId) return;
      const current = getValues(`lines.${index}.product_id`);
      if (String(current) === String(productId)) return;
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
      const pCount = Number(line?.pallet_count || 0);
      const pQty = Number(line?.qty_per_pallet || 0);
      const bCount = Number(line?.box_count || 0);
      const bQty = Number(line?.qty_per_box || 0);
      const packed = pCount * pQty + bCount * bQty;
      if (packed > 0) {
        const short =
          shortOverride !== undefined ? parseShortQty(shortOverride) : parseShortQty(line.short_quantity);
        setValue(`lines.${index}.quantity`, Math.max(0, packed - short), { shouldDirty: true });
      }
    });
  };

  const onPalletChange = (index) => {
    if (applyingParsedRef.current) return;
    const pCount = Number(getValues(`lines.${index}.pallet_count`) || 0);
    const pQty = Number(getValues(`lines.${index}.qty_per_pallet`) || 0);
    if (pCount > 0 || pQty > 0) {
      setValue(`lines.${index}.box_count`, 0, { shouldDirty: true });
      setValue(`lines.${index}.qty_per_box`, 0, { shouldDirty: true });
    }
    recalcLineQty(index);
  };

  const onBoxChange = (index) => {
    if (applyingParsedRef.current) return;
    if (isPalletMode) return;
    const bCount = Number(getValues(`lines.${index}.box_count`) || 0);
    const bQty = Number(getValues(`lines.${index}.qty_per_box`) || 0);
    if (bCount > 0 || bQty > 0) {
      setValue(`lines.${index}.pallet_count`, 0, { shouldDirty: true });
      setValue(`lines.${index}.qty_per_pallet`, 0, { shouldDirty: true });
    }
    recalcLineQty(index);
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
          const isPallet = isPalletMode || (Number(line.pallet_count || 0) > 0 && Number(line.box_count || 0) === 0);
          return {
            product_id: line.product_id,
            uom_id: product?.uom_id || catalog?.uom_id,
            heat_number: String(line.heat_number || '').trim() || undefined,
            pallet_count: isPallet ? Number(line.pallet_count || 0) : 0,
            qty_per_pallet: isPallet ? Number(line.qty_per_pallet || 0) : 0,
            box_count: !isPallet ? Number(line.box_count || 0) : 0,
            qty_per_box: !isPallet ? Number(line.qty_per_box || 0) : 0,
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
            packing_detail: buildPackingDetail(line, isPallet),
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

  const isPalletModeRef = useRef(isPalletMode);
  isPalletModeRef.current = isPalletMode;

  const handleParsedDocument = useCallback((data) => {
    lastParseKeyRef.current = null;
    setParsedData(data);
  }, []);

  const getFormPalletMode = useCallback(() => {
    if (isPalletModeRef.current) return true;
    const id = getValues('vendor_id');
    const v = vendors.find((x) => String(x.id) === String(id));
    return isPalletSupplier(v);
  }, [getValues, vendors]);

  return (
    <InwardDocumentUpload
      multiple
      getFormPalletMode={getFormPalletMode}
      onParsed={handleParsedDocument}
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
              <div className="flex items-center justify-between">
                <label htmlFor="vendor_id" className="text-xs font-medium text-gray-600">Supplier</label>
                {vendor && (
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide ${
                      isPalletMode
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                    title={isPalletMode ? 'Pallet Supplier: AGRASEN, FALSAN, UNIQUE, AASHITA' : 'C/Box Supplier: DEEPESH, PUSHP, PERFECT, T POINT'}
                  >
                    Packaging: {isPalletMode ? 'Pallets' : 'C/Boxes'}
                  </span>
                )}
              </div>
              <select id="vendor_id" {...register('vendor_id', { required: true })} className={lineSelectClass}>
                <option value="">Select Supplier</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.packaging_type === 'PALLET' || isPalletSupplier(v) ? 'Pallets' : 'C/Boxes'})
                  </option>
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
              <div className="min-w-[128rem] px-1">
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
                      <th className={`${thBase} ${isPalletMode ? 'bg-blue-50 text-blue-700 font-bold border-t border-l border-blue-200' : 'text-gray-400'}`}>Pallets</th>
                      <th className={`${thBase} ${isPalletMode ? 'bg-blue-50 text-blue-700 font-bold border-t border-r border-blue-200' : 'text-gray-400'}`}>Qty / Pallet</th>
                      <th className={`${thBase} ${!isPalletMode ? 'bg-amber-50 text-amber-700 font-bold border-t border-l border-amber-200' : 'text-gray-400'}`}>Boxes</th>
                      <th className={`${thBase} ${!isPalletMode ? 'bg-amber-50 text-amber-700 font-bold border-t border-r border-amber-200' : 'text-gray-400'}`}>Qty / Box</th>
                      <th className={thBase}>Short Qty</th>
                      <th className={`${thBase} min-w-[7rem]`}>Qty</th>
                      <th className={`${thBase} min-w-[8.5rem] w-36`}>Heat No.</th>
                      <th className={`${thBase} w-[6.5rem]`}>Part No</th>
                      <th className={thBase}>UOM</th>
                      <th className={`${thBase} min-w-[5.5rem]`}>Rate</th>
                      <th className={`${thBase} min-w-[3.5rem]`}>GST%</th>
                      <th className={`${thBase} min-w-[6.5rem]`}>Taxable ₹</th>
                      <th className={`${thBase} min-w-[6rem]`}>Ring Wt</th>
                      <th className={`${thBase} min-w-[6rem]`}>Packing Wt</th>
                      <th className={`${thBase} min-w-[6rem]`}>Gross Wt</th>
                      <th className={`${thBase} min-w-[6rem]`}>Net Wt</th>
                      <th className={`${thBase} min-w-[6.5rem]`}>Total ₹</th>
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
                          <td className={`${tdR} ${isPalletMode ? 'bg-blue-50/20' : ''}`}>
                            <input
                              type="text"
                              inputMode="numeric"
                              className={`${numInputRightClass} ${isPalletMode ? 'border-blue-300 font-medium' : ''}`}
                              {...register(`lines.${index}.pallet_count`, {
                                onChange: () => onPalletChange(index),
                              })}
                            />
                          </td>
                          <td className={`${tdR} ${isPalletMode ? 'bg-blue-50/20' : ''}`}>
                            <input
                              type="text"
                              inputMode="decimal"
                              title={String(watchedLines[index]?.qty_per_pallet ?? '')}
                              className={`${numInputRightClass} ${isPalletMode ? 'border-blue-300 font-medium' : ''}`}
                              {...register(`lines.${index}.qty_per_pallet`, {
                                onChange: () => onPalletChange(index),
                              })}
                            />
                          </td>
                          <td className={`${tdR} ${!isPalletMode ? 'bg-amber-50/20' : ''}`}>
                            <input
                              type="text"
                              inputMode="numeric"
                              className={`${numInputRightClass} ${!isPalletMode ? 'border-amber-300 font-medium' : ''}`}
                              {...register(`lines.${index}.box_count`, {
                                onChange: () => onBoxChange(index),
                              })}
                            />
                          </td>
                          <td className={`${tdR} ${!isPalletMode ? 'bg-amber-50/20' : ''}`}>
                            <input
                              type="text"
                              inputMode="decimal"
                              title={String(watchedLines[index]?.qty_per_box ?? '')}
                              className={`${numInputRightClass} ${!isPalletMode ? 'border-amber-300 font-medium' : ''}`}
                              {...register(`lines.${index}.qty_per_box`, {
                                onChange: () => onBoxChange(index),
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
                          <td className={qtyTotalTdClass}>
                            <input
                              type="text"
                              inputMode="decimal"
                              readOnly={packingQty(watchedLines[index] || {}) > 0}
                              title={String(watchedLines[index]?.quantity ?? '')}
                              className={`${qtyTotalInputClass}${
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
                          <td className={rateInputTdClass}>
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
                          <td className={rateInputTdClass}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              readOnly
                              {...register(`lines.${index}.gst_percent`)}
                            />
                          </td>
                          <td className={`${amountDisplayTdClass} text-xs text-gray-600`}>
                            {formatAmount(lineTotals[index]?.taxable ?? 0)}
                          </td>
                          <td className={wtInputTdClass}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className={numInputRightClass}
                              {...register(`lines.${index}.per_ring_weight`)}
                            />
                          </td>
                          <td className={wtInputTdClass}>
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
                          <td className={`${amountDisplayTdClass} text-xs font-medium text-gray-800`}>
                            {wt?.qty ? formatWt(wt.gross) : '—'}
                          </td>
                          <td className={`${amountDisplayTdClass} text-xs font-semibold text-gray-900`}>
                            {wt?.qty ? formatWt(wt.weightTotal) : '—'}
                          </td>
                          <td className={`${amountDisplayTdClass} text-sm font-medium text-gray-900`}>
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
