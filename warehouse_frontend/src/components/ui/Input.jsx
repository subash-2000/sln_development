import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Enterprise Input Component
 */
const Input = React.forwardRef(({ 
  className, 
  type = 'text',
  label,
  error,
  helperText,
  isRequired = false,
  id,
  ...props 
}, ref) => {
  const inputId = id || props.name;

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-gray-700">
          {label}
          {isRequired && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <input
        id={inputId}
        type={type}
        ref={ref}
        className={twMerge(
          'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm',
          'placeholder:text-gray-400',
          'focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all duration-200',
          'disabled:bg-gray-50 disabled:cursor-not-allowed',
          error && 'border-red-500 focus:ring-red-500',
          className
        )}
        {...props}
      />
      {error && (
        <p className="text-xs text-red-500 font-medium">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-xs text-gray-500">{helperText}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
