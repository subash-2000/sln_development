/** Map legacy UI location types to backend LocationType enum values. */
const LEGACY_LOCATION_TYPE = {
  STORAGE: 'INTERNAL',
  SHIPPING: 'DISPATCH',
  PICKING: 'INTERNAL',
  VIRTUAL: 'INTERNAL',
};

export function normalizeLocationType(value) {
  const raw = (value || 'INTERNAL').toString().trim().toUpperCase();
  return LEGACY_LOCATION_TYPE[raw] || raw;
}

const optionalText = (value) => {
  const trimmed = value != null ? String(value).trim() : '';
  return trimmed || null;
};

export function buildLocationCreatePayload(form) {
  return {
    warehouse_id: form.warehouse_id,
    code: form.code?.trim(),
    name: form.name?.trim(),
    location_type: normalizeLocationType(form.location_type),
    storage_type: 'BIN',
    zone: optionalText(form.zone),
    aisle: optionalText(form.aisle),
    shelf: optionalText(form.shelf),
    bin: optionalText(form.bin),
    allow_mixed_products: true,
    allow_mixed_vendors: true,
    status: form.is_active === false ? 'INACTIVE' : 'ACTIVE',
  };
}

export function buildLocationUpdatePayload(form) {
  return {
    name: form.name?.trim(),
    location_type: normalizeLocationType(form.location_type),
    zone: optionalText(form.zone),
    aisle: optionalText(form.aisle),
    shelf: optionalText(form.shelf),
    bin: optionalText(form.bin),
    status: form.is_active === false ? 'INACTIVE' : 'ACTIVE',
  };
}

export function getLocationErrorMessage(error, fallback) {
  if (error?.message) return error.message;
  const detail = error?.details;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  }
  if (typeof detail === 'string') return detail;
  return fallback;
}
