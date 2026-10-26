import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const Breadcrumb = ({ items = [] }) => {
  if (!items.length) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center text-sm text-gray-500">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className="flex items-center">
            {index > 0 && <ChevronRight size={14} className="mx-1 text-gray-400" />}
            {item.to && !isLast ? (
              <Link to={item.to} className="hover:text-primary-700">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'text-gray-700 font-medium' : ''}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
