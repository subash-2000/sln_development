import React, { useState, useRef, useEffect } from 'react';
import { twMerge } from 'tailwind-merge';

const Dropdown = ({ trigger, children, align = 'right', className, closeOnClick = true }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div className={twMerge('relative inline-block text-left', className)} ref={containerRef}>
      <div onClick={() => setIsOpen(!isOpen)} className="cursor-pointer">
        {trigger}
      </div>

      {isOpen && (
        <div
          className={twMerge(
            'absolute mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50',
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          <div className="py-1" role="menu" aria-orientation="vertical">
            {closeOnClick
              ? React.Children.map(children, (child) => {
                  if (React.isValidElement(child)) {
                    return React.cloneElement(child, {
                      onClick: (e) => {
                        child.props.onClick?.(e);
                        setIsOpen(false);
                      },
                    });
                  }
                  return child;
                })
              : children}
          </div>
        </div>
      )}
    </div>
  );
};

const DropdownItem = ({ children, onClick, className, variant = 'default' }) => {
  const variants = {
    default: 'text-gray-700 hover:bg-gray-100',
    danger: 'text-red-600 hover:bg-red-50',
  };

  return (
    <button
      className={twMerge(
        'block w-full text-left px-4 py-2 text-sm transition-colors',
        variants[variant],
        className
      )}
      role="menuitem"
      onClick={onClick}
    >
      {children}
    </button>
  );
};

Dropdown.Item = DropdownItem;

export default Dropdown;
