/**
 * Safely sorts any list of items/options in ascending alphabetical/natural order.
 * @param {Array} list - Array of objects or strings to sort
 * @param {Function} [keyExtractor] - Optional accessor function
 * @returns {Array} Sorted new array copy
 */
export const sortAscending = (list, keyExtractor) => {
  if (!Array.isArray(list)) return [];
  return [...list].sort((a, b) => {
    let valA = keyExtractor
      ? keyExtractor(a)
      : a?.label ?? a?.name ?? a?.code ?? a?.title ?? a?.sku ?? a?.username ?? String(a ?? '');
    let valB = keyExtractor
      ? keyExtractor(b)
      : b?.label ?? b?.name ?? b?.code ?? b?.title ?? b?.sku ?? b?.username ?? String(b ?? '');
    valA = valA == null ? '' : String(valA).trim();
    valB = valB == null ? '' : String(valB).trim();
    return valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' });
  });
};
