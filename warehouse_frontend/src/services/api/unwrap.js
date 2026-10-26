/**
 * FastAPI StandardResponse helpers.
 * Envelope: { success, message, data, pagination, request_id }
 */
export const unwrapData = (envelope) => envelope?.data ?? null;

export const unwrapList = (envelope) => ({
  items: Array.isArray(envelope?.data) ? envelope.data : [],
  pagination: envelope?.pagination ?? {
    page: 1,
    page_size: 25,
    total: 0,
    total_pages: 0,
  },
  message: envelope?.message,
  requestId: envelope?.request_id,
});

export const buildListParams = (params = {}) => {
  const query = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'ALL') {
      return;
    }
    query[key] = value;
  });
  return query;
};
