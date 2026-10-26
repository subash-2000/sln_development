import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Hammer, ArrowLeft, Home, Sparkles } from 'lucide-react';
import PageHeader from './PageHeader';
import Card from '../ui/Card';
import Button from '../ui/Button';

const UnderDevelopmentPage = ({
  title = 'Under Development',
  moduleName = 'This feature',
  description = 'This screen and creation workflow is currently in active development.',
  breadcrumbs,
  backTo,
}) => {
  const navigate = useNavigate();

  const defaultBreadcrumbs = [
    { label: 'Dashboard', to: '/dashboard' },
    { label: moduleName, to: backTo || -1 },
    { label: title },
  ];

  const handleBack = () => {
    if (backTo) {
      navigate(backTo);
    } else {
      navigate(-1);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={breadcrumbs || defaultBreadcrumbs}
      />

      <Card className="max-w-2xl mx-auto border-dashed border-2 border-amber-200 bg-gradient-to-b from-amber-50/40 to-white shadow-sm overflow-hidden">
        <Card.Body className="py-12 px-6 sm:px-10 text-center space-y-5">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-700 shadow-inner">
            <Hammer className="w-8 h-8 animate-bounce" />
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            Under Development
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-gray-900 tracking-tight">
              {title} Form Coming Soon
            </h2>
            <p className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
              The {moduleName} creation and management workflow is currently being built.
              Please check back soon or explore other active modules.
            </p>
          </div>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-3">
            <Button
              variant="primary"
              onClick={handleBack}
              leftIcon={<ArrowLeft className="w-4 h-4" />}
            >
              Back to {moduleName}
            </Button>
            <Button
              variant="secondary"
              onClick={() => navigate('/dashboard')}
              leftIcon={<Home className="w-4 h-4" />}
            >
              Go to Dashboard
            </Button>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default UnderDevelopmentPage;
