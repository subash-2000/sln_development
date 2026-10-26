/** Pallet vs cotton box (matches backend ProductPackageTrackingType). */
export const PACKAGE_TRACKING_TYPES = [
  { value: 'PALLET_NUMBER', label: 'Pallet number' },
  { value: 'COTTON_BOX', label: 'Cotton box' },
];

export const packageTrackingTypeLabel = (value) =>
  PACKAGE_TRACKING_TYPES.find((d) => d.value === value)?.label || value || '—';
