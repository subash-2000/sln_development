import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateLocation } from '../hooks/use-locations';
import LocationForm from '../components/LocationForm';
import PageHeader from '../../../components/common/PageHeader';

const LocationCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createLocation, isPending } = useCreateLocation();

  const handleSubmit = async (data) => {
    try {
      await createLocation(data);
      navigate('/locations');
    } catch (error) {
      console.error('Failed to create location:', error);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add New Location"
        description="Define a new storage or processing area within a warehouse."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Locations', to: '/locations' },
          { label: 'Add Location' },
        ]}
      />
      <LocationForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default LocationCreatePage;
