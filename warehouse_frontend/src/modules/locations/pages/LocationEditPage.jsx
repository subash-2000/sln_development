import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLocation, useUpdateLocation } from '../hooks/use-locations';
import LocationForm from '../components/LocationForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';
import {
  buildLocationUpdatePayload,
  getLocationErrorMessage,
} from '../utils/locationPayload';

const LocationEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: location, isLoading: isFetching } = useLocation(id);
  const { mutateAsync: updateLocation, isPending: isUpdating } = useUpdateLocation();
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (data) => {
    setErrorMessage(null);
    try {
      await updateLocation({ id, data: buildLocationUpdatePayload(data) });
      navigate('/locations');
    } catch (error) {
      console.error('Failed to update location:', error);
      setErrorMessage(getLocationErrorMessage(error, 'Failed to update location.'));
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
        serverError={errorMessage}
      />
    </div>
  );
};

export default LocationEditPage;
