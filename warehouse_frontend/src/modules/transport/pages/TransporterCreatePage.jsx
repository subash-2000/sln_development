import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import PageHeader from '../../../components/common/PageHeader';
import TransporterForm from '../components/TransporterForm';
import { useCreateTransporter } from '../hooks/use-transporters';

const TransporterCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createTransporter, isPending } = useCreateTransporter();

  const handleSubmit = async (data) => {
    const created = await createTransporter({
      ...data,
      company_id: companyContext,
    });
    navigate(`/transport/${created.id}`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Transporter"
        description="Register a logistics partner for outward dispatch and gate pass."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Transport', to: '/transport' },
          { label: 'New' },
        ]}
      />
      <TransporterForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default TransporterCreatePage;
