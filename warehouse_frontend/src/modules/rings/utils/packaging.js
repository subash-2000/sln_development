/**
 * Helper to determine if a supplier sends material on Pallets or in C/Boxes.
 * Pallet suppliers: AGRASEN, FALSAN, UNIQUE, AASHITA.
 * C/Box suppliers: DEEPESH ENG WORKS, PUSHP ENT, PERFECT, T POINT.
 */
export const isPalletSupplier = (vendor) => {
  if (!vendor) return false;
  const pkg = String(vendor.packaging_type || '').toUpperCase();
  if (pkg.includes('PALLET')) return true;
  if (pkg.includes('BOX')) return false;
  const blob = `${vendor.code || ''} ${vendor.name || ''}`.toUpperCase();
  return /AGRASEN|FALSAN|UNIQUE|AASHITA/i.test(blob);
};
