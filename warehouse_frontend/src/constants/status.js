export const STATUS_VARIANTS = {
  ACTIVE: 'success',
  INACTIVE: 'neutral',
  ARCHIVED: 'neutral',
  SUSPENDED: 'warning',
  BLOCKED: 'danger',
  DRAFT: 'neutral',
  PENDING: 'warning',
  APPROVED: 'info',
  REJECTED: 'danger',
  CANCELLED: 'danger',
  CANCELED: 'danger',
  COMPLETED: 'success',
  POSTED: 'info',
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  CONFIRMED: 'info',
  OPEN: 'info',
  CLOSED: 'neutral',
  IN_PROGRESS: 'info',
  DISPATCHED: 'info',
  DELIVERED: 'success',
  RECEIVED: 'success',
  FROZEN: 'warning',
  COUNTING: 'info',
  AVAILABLE: 'success',
  RESERVED: 'warning',
  PACKED: 'info',
  MATERIAL_ISSUED: 'info',
  IN_PROCESS: 'info',
  GOODS_RECEIVED: 'success',
  CALCULATING: 'warning',
  CALCULATED: 'info',
  INVOICED: 'success',
  EXPIRED: 'warning',
  TERMINATED: 'danger',
  INSPECTED: 'info',
  ASSIGNED: 'info',
  DONE: 'success',
  STOCK_OK: 'success',
  AGING: 'warning',
  OVERDUE: 'danger',
  UNKNOWN: 'neutral',
};

export const STATUS_DISPLAY = {
  STOCK_OK: 'STOCK OK',
  AGING: 'Aging',
  OVERDUE: 'Review',
};

export const getStatusVariant = (status) => {
  if (!status) return 'neutral';
  return STATUS_VARIANTS[String(status).toUpperCase()] || 'neutral';
};

export const getStatusDisplay = (status) => {
  if (!status) return 'Unknown';
  const key = String(status).toUpperCase();
  return STATUS_DISPLAY[key] || status;
};

export const isEntityActive = (item) => {
  if (!item) return false;
  if (item.status !== undefined && item.status !== null) {
    return String(item.status).toUpperCase() === 'ACTIVE';
  }
  return Boolean(item.is_active);
};
