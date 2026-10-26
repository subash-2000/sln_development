import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateLogisticsInward } from '../hooks/use-logistics';
import LogisticsInwardForm from '../components/LogisticsInwardForm';
import InwardDocumentUpload from '../components/InwardDocumentUpload';
import PageHeader from '../../../components/common/PageHeader';

const LogisticsInwardCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createInward, isPending } = useCreateLogisticsInward();
  const [parsedData, setParsedData] = useState(null);

  const handleSubmit = async (data) => {
    try {
      const tx = await createInward(data);
      if (tx?.id) {
        navigate(`/logistics/inward/${tx.id}`);
      } else {
        navigate('/logistics/inward');
      }
    } catch (error) {
      console.error('Failed to create inward:', error);
    }
  };

  return (
    <InwardDocumentUpload
      onParsed={setParsedData}
      render={({ trigger, feedback }) => (
        <div className="space-y-6">
          <PageHeader
            title="New Inward Transaction"
            description="Record a new receipt of materials into the warehouse."
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Logistics' },
              { label: 'Inward', to: '/logistics/inward' },
              { label: 'New Inward' },
            ]}
            actions={trigger}
          />
          {feedback}
          <LogisticsInwardForm
            onSubmit={handleSubmit}
            isLoading={isPending}
            parsedData={parsedData}
          />
        </div>
      )}
    />
  );
};

export default LogisticsInwardCreatePage;
