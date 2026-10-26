export const formatAgeStatusLabel = (status) => {
  const key = String(status || '').toUpperCase();
  const map = {
    STOCK_OK: 'STOCK OK',
    AGING: 'Aging',
    OVERDUE: 'Review',
    UNKNOWN: '—',
  };
  return map[key] || status || '—';
};
