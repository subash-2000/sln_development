/**
 * Standard API Error Class
 */
export class ApiError extends Error {
  constructor(message, status, code, details, requestId) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

/**
 * Normalizes backend error responses into ApiError instances
 */
export const normalizeError = async (error) => {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    const { data, status, headers } = error.response;
    let payload = data;
    if (data instanceof Blob && data.type?.includes('json')) {
      try {
        payload = JSON.parse(await data.text());
      } catch {
        payload = null;
      }
    }
    const requestId = headers['x-request-id'] || payload?.request_id;

    let msg = payload?.message;
    if (!msg && payload?.detail) {
      if (Array.isArray(payload.detail)) {
        msg = payload.detail.map((d) => d.msg || `${d.loc?.join('.')}: ${d.msg}`).join('\n');
      } else {
        msg = String(payload.detail);
      }
    }

    return new ApiError(
      msg || 'An unexpected error occurred',
      status,
      payload?.error_code || 'SERVER_ERROR',
      payload?.details || payload?.detail || null,
      requestId
    );
  } else if (error.request) {
    // The request was made but no response was received
    return new ApiError(
      'Network error. Please check your connection.',
      0,
      'NETWORK_ERROR',
      null,
      null
    );
  } else {
    // Something happened in setting up the request that triggered an Error
    return new ApiError(
      error.message || 'Unknown error occurred',
      null,
      'UNKNOWN_ERROR',
      null,
      null
    );
  }
};
