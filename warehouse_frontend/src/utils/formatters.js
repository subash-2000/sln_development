/**
 * Utility functions for formatting currency and numbers
 */

/**
 * Formats a number as currency (INR by default)
 * @param {number} amount - The amount to format
 * @param {string} currency - The currency code (default: 'INR')
 * @param {string} locale - The locale to use (default: 'en-IN')
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'INR', locale = 'en-IN') => {
  if (amount === null || amount === undefined) return '-';
  
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Formats a number with locale-specific separators
 * @param {number} number - The number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @param {string} locale - The locale to use (default: 'en-IN')
 * @returns {string} Formatted number string
 */
export const formatNumber = (number, decimals = 2, locale = 'en-IN') => {
  if (number === null || number === undefined) return '-';

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(number);
};

/**
 * Formats a date string to a user-friendly format
 * @param {string|Date} date - The date to format
 * @param {string} locale - The locale to use (default: 'en-IN')
 * @returns {string} Formatted date string
 */
export const formatDate = (date, locale = 'en-IN') => {
  if (!date) return '-';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '-';
  
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(d);
};

export const formatDateTime = (date, locale = 'en-IN') => {
  if (!date) return '-';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return '-';
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
};

export const formatQuantity = (value, uom) => {
  if (value === null || value === undefined) return '-';
  const formatted = formatNumber(value);
  return uom ? `${formatted} ${uom}` : formatted;
};

export const formatPercentage = (value) => {
  if (value === null || value === undefined) return '-';
  return `${formatNumber(value)}%`;
};
