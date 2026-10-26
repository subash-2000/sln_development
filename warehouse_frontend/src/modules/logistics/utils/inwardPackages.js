const PACKAGES_TAG = '[INWARD_PACKAGES]';

export const parseInwardLineRemarks = (remarks) => {
  if (!remarks) {
    return { part_number: null, package_count: null, hsn_code: null, line_remark: '' };
  }
  const part = remarks.match(/Part:\s*([^|]+)/)?.[1]?.trim() || null;
  const pkgs = remarks.match(/Pkgs:\s*(\d+)/)?.[1];
  const hsn = remarks.match(/HSN:\s*([^|]+)/)?.[1]?.trim() || null;
  const userParts = remarks
    .split('|')
    .map((s) => s.trim())
    .filter(
      (seg) =>
        seg &&
        !seg.startsWith('Part:') &&
        !seg.startsWith('Pkgs:') &&
        !seg.startsWith('HSN:') &&
        !seg.startsWith('Boxes:')
    );
  return {
    part_number: part,
    package_count: pkgs != null ? Number(pkgs) : null,
    hsn_code: hsn,
    line_remark: userParts.join(' | ').trim(),
  };
};

export const parsePackagesFromRemarks = (remarks) => {
  if (!remarks || !remarks.includes(PACKAGES_TAG)) return null;
  try {
    const idx = remarks.indexOf(PACKAGES_TAG);
    const raw = remarks.slice(idx + PACKAGES_TAG.length).trim();
    if (!raw) return null;
    const jsonPart = raw.split(' | ')[0].trim();
    return JSON.parse(jsonPart);
  } catch {
    return null;
  }
};
