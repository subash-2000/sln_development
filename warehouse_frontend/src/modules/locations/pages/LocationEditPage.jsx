import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLocation, useUpdateLocation } from '../hooks/use-locations';
import LocationForm from '../components/LocationForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const LocationEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: location, isLoading: isFetching } = useLocation(id);
  const { mutateAsync: updateLocation, isPending: isUpdating } = useUpdateLocation();

  const handleSubmit = async (data) => {
    try {
      await updateLocation({ id, data });
      navigate('/locations');
    } catch (error) {
      console.error('Failed to update location:', error);
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Location"
        description="Update location coordinates and operational type."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Locations', to: '/locations' },
          { label: 'Edit Location' },
        ]}
      />
      <LocationForm 
        initialData={location} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default LocationEditPage;
