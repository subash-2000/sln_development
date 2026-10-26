/** Single-line label for product filter (avoids "SKU — SKU" duplicates). */
export function formatProductOptionLabel(product) {
  const sku = (product?.sku || '').trim();
  const name = (product?.name || '').trim();
  if (!name && !sku) return '—';
  if (!sku) return name;
  if (!name) return sku;
  const skuU = sku.toUpperCase();
  const nameU = name.toUpperCase();
  if (skuU === nameU) return name;
  if (nameU.startsWith(skuU) || nameU.includes(skuU)) return name;
  return `${sku} — ${name}`;
}
