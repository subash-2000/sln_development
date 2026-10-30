import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Building2, Truck } from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import TransporterForm from '../components/TransporterForm';
import TransporterVehiclesTab from '../components/TransporterVehiclesTab';
import { useTransporter, useUpdateTransporter } from '../hooks/use-transporters';

const TransporterEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('general'); // 'general' | 'vehicles'

  const { data: transporter, isLoading, error, refetch } = useTransporter(id);
  const { mutateAsync: updateTransporter, isPending } = useUpdateTransporter();

  if (isLoading) return <Loader fullPage />;
  if (error || !transporter) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-600">Transporter not found.</p>
        <Button className="mt-4" onClick={() => navigate('/transport')}>
          Back to list
        </Button>
      </Card>
    );
  }

  const handleUpdate = async (data) => {
    await updateTransporter({ id: transporter.id, data });
    refetch();
  };

  const vehiclesCount = transporter.vehicles_count ?? (transporter.vehicles?.length || 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title={transporter.name}
        description={`Transporter Code: ${transporter.code} • ${vehiclesCount} vehicle${vehiclesCount === 1 ? '' : 's'} registered`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Transport', to: '/transport' },
          { label: transporter.code },
        ]}
      />

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 gap-4">
        <button
          type="button"
          onClick={() => setActiveTab('general')}
          className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'general'
              ? 'border-blue-600 text-blue-600 font-semibold'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <Building2 size={16} />
          <span>General Details</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('vehicles')}
          className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'vehicles'
              ? 'border-blue-600 text-blue-600 font-semibold'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <Truck size={16} />
          <span>Vehicles Fleet</span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-bold ${
              activeTab === 'vehicles'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            {vehiclesCount}
          </span>
        </button>
      </div>

      {activeTab === 'general' ? (
        <TransporterForm
          initialData={transporter}
          onSubmit={handleUpdate}
          isLoading={isPending}
          isEdit
        />
      ) : (
        <TransporterVehiclesTab transporter={transporter} onVehiclesChanged={refetch} />
      )}
    </div>
  );
};

export default TransporterEditPage;
