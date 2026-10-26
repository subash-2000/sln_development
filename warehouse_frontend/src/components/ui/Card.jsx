import React from 'react';
import { twMerge } from 'tailwind-merge';

/**
 * Enterprise Card Component
 */
const Card = ({ children, className, ...props }) => {
  return (
    <div 
      className={twMerge('bg-white border border-gray-100 rounded-xl shadow-clay-sm', className)} 
      {...props}
    >
      {children}
    </div>
  );
};

const CardHeader = ({ children, className, ...props }) => (
  <div className={twMerge('px-6 py-4 border-b border-gray-100', className)} {...props}>
    {children}
  </div>
);

const CardTitle = ({ children, className, ...props }) => (
  <h3 className={twMerge('text-lg font-semibold text-gray-900', className)} {...props}>
    {children}
  </h3>
);

const CardBody = ({ children, className, ...props }) => (
  <div className={twMerge('p-6', className)} {...props}>
    {children}
  </div>
);

const CardFooter = ({ children, className, ...props }) => (
  <div className={twMerge('px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-xl', className)} {...props}>
    {children}
  </div>
);

Card.Header = CardHeader;
Card.Title = CardTitle;
Card.Body = CardBody;
Card.Footer = CardFooter;

export default Card;
export { CardHeader, CardTitle, CardBody, CardFooter };
