/**
 * Pallet suppliers: AGRASEN, FALSAN, UNIQUE, AASHITA.
 * C/Box suppliers: DEEPESH, PUSHP, PERFECT, T POINT.
 */
export const PALLET_SUPPLIER_RE = /AGRASEN|FALSAN|UNIQUE|AASHITA/i;

export const isPalletSupplierBlob = (text) => {
  if (!text) return false;
  return PALLET_SUPPLIER_RE.test(String(text));
};

export const isPalletSupplier = (vendor) => {
  if (!vendor) return false;
  const blob = `${vendor.code || ''} ${vendor.name || ''}`.toUpperCase();
  if (PALLET_SUPPLIER_RE.test(blob)) return true;
  const pkg = String(vendor.packaging_type || '').toUpperCase().replace(/\s/g, '');
  if (pkg.includes('PALLET')) return true;
  if (pkg === 'C_BOX' || pkg === 'CBOX' || pkg.includes('C/BOX')) return false;
  if (pkg.includes('BOX')) return false;
  return false;
};

/** Bulk NOS lines (e.g. NHB steel balls) — qty only, no box/pallet split from invoice OCR. */
export const isBulkInwardLine = (item) => {
  if (!item) return false;
  const uom = String(item.uom || item.uom_code || '').toUpperCase();
  const qty = Number(item.quantity || 0);
  if (qty < 1000 || uom !== 'NOS') return false;
  const blob = `${item.description || ''} ${item.sku_guess || ''}`.toLowerCase();
  if (/\d+\.?\d*\s*mm|steel\s*ball|nhb/i.test(blob)) return true;
  return qty >= 10_000;
};

/** Normalize API parse lines: pallet supplier counts must not stay in box fields. */
export const normalizeParsedItemsPacking = (items, usePallet) => {
  if (!items?.length) return items;
  return items.map((item) => {
    if (isBulkInwardLine(item)) {
      return {
        ...item,
        pallet_count: 0,
        qty_per_pallet: 0,
        box_count: 0,
        qty_per_box: 0,
        package_count: null,
      };
    }
    if (!usePallet) return item;
    const p = Number(item.pallet_count || 0);
    let b = Number(item.box_count || 0);
    const pkg = Number(item.package_count || 0);
    if (p > 0 && b === 0) return item;
    if (b <= 0 && pkg > 0) b = pkg;
    if (b <= 0) return item;
    const pQty = Number(item.qty_per_pallet || 0);
    const bQty = Number(item.qty_per_box || 0);
    const qty = Number(item.quantity || 0);
    const count = p || b;
    const per = pQty || bQty || (qty > 0 && count > 0 ? qty / count : 0);
    return {
      ...item,
      pallet_count: count,
      qty_per_pallet: per,
      box_count: 0,
      qty_per_box: 0,
      package_count: count,
    };
  });
};
