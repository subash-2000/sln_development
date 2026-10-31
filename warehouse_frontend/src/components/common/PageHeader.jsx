import Button from '../ui/Button';
import Breadcrumb from '../navigation/Breadcrumb';

const PageHeader = ({ title, description, breadcrumbs, actions, children }) => {
  const actionContent = actions || children;
  return (
    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
      <div className="space-y-1">
        {breadcrumbs && <Breadcrumb items={breadcrumbs} />}
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {description && <p className="text-gray-500 text-sm">{description}</p>}
      </div>
      {actionContent ? <div className="flex items-center gap-2 shrink-0">{actionContent}</div> : null}
    </div>
  );
};

export default PageHeader;
export { Button };
