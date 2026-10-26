import { twMerge } from 'tailwind-merge';

const QuickFilters = ({ options = [], value, onChange }) => {
  if (!options.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange?.(option.value)}
            className={twMerge(
              'px-3 py-1.5 rounded-full text-sm border transition-colors',
              isActive
                ? 'bg-primary-50 text-primary-700 border-primary-200'
                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
};

export default QuickFilters;
