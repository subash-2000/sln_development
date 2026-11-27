import Button from '../ui/Button';
import Breadcrumb from '../navigation/Breadcrumb';

const PageHeader = ({ title, breadcrumbs, actions, children }) => {
  const actionContent = actions || children;
  return (
    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
      <div className="space-y-1">
        {breadcrumbs && <Breadcrumb items={breadcrumbs} />}
        {title && <h1 className="sr-only">{title}</h1>}
      </div>
      {actionContent ? <div className="flex items-center gap-2 shrink-0">{actionContent}</div> : null}
    </div>
  );
};

export default PageHeader;
export { Button };
