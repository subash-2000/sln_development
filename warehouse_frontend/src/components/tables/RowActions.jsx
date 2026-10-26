import React from 'react';
import { MoreVertical, Eye, Edit, Copy, Trash2, Power, CheckCircle, XCircle } from 'lucide-react';
import Dropdown from '../ui/Dropdown';
import Button from '../ui/Button';

const RowActions = ({ actions = [] }) => {
  if (!actions || actions.length === 0) return null;

  const getIcon = (type) => {
    switch (type) {
      case 'view': return <Eye size={16} className="mr-2" />;
      case 'edit': return <Edit size={16} className="mr-2" />;
      case 'duplicate': return <Copy size={16} className="mr-2" />;
      case 'delete': return <Trash2 size={16} className="mr-2" />;
      case 'deactivate': return <Power size={16} className="mr-2 text-amber-600" />;
      case 'activate': return <Power size={16} className="mr-2 text-green-600" />;
      case 'approve': return <CheckCircle size={16} className="mr-2" />;
      case 'reject': return <XCircle size={16} className="mr-2" />;
      default: return null;
    }
  };

  return (
    <Dropdown
      trigger={
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
          <MoreVertical size={18} className="text-gray-500" />
        </Button>
      }
    >
      {actions.map((action, index) => {
        if (action.hidden) return null;
        
        return (
          <Dropdown.Item
            key={index}
            onClick={action.onClick}
            variant={action.variant || (action.type === 'delete' ? 'danger' : 'default')}
            className="flex items-center"
          >
            {getIcon(action.type)}
            {action.label}
          </Dropdown.Item>
        );
      })}
    </Dropdown>
  );
};

export default RowActions;
