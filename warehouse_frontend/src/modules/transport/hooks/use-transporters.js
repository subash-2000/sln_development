import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { transportersApi } from '../api/transporters.api';

export const useTransporters = (params) =>
  useQuery({
    queryKey: ['transporters', params],
    queryFn: () => transportersApi.list(params),
    placeholderData: (previous) => previous,
  });

export const useTransporter = (id) =>
  useQuery({
    queryKey: ['transporters', id],
    queryFn: () => transportersApi.getById(id),
    enabled: Boolean(id),
  });

export const useCreateTransporter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: transportersApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['transporters'] }),
  });
};

export const useUpdateTransporter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => transportersApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
      queryClient.invalidateQueries({ queryKey: ['transporters', id] });
    },
  });
};

// ---------------------------------------------------------
// Vehicle Sub-Master React Query Hooks
// ---------------------------------------------------------

export const useTransporterVehicles = (transporterId, params) =>
  useQuery({
    queryKey: ['transporter-vehicles', transporterId, params],
    queryFn: () => transportersApi.listVehicles(transporterId, params),
    enabled: Boolean(transporterId),
    placeholderData: (previous) => previous,
  });

export const useAllVehicles = (params) =>
  useQuery({
    queryKey: ['transporter-vehicles-all', params],
    queryFn: () => transportersApi.listAllVehicles(params),
    placeholderData: (previous) => previous,
  });

export const useCreateVehicle = (defaultTransporterId) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => {
      const targetTransporterId = data.transporter_id || defaultTransporterId;
      return transportersApi.createVehicle(targetTransporterId, data);
    },
    onSuccess: (_, variables) => {
      const tid = variables?.transporter_id || defaultTransporterId;
      if (tid) {
        queryClient.invalidateQueries({ queryKey: ['transporter-vehicles', tid] });
        queryClient.invalidateQueries({ queryKey: ['transporters', tid] });
      }
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles-all'] });
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
    },
  });
};

export const useUpdateVehicle = (defaultTransporterId) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ vehicleId, transporterId, data }) => {
      const targetTransporterId = transporterId || data?.transporter_id || defaultTransporterId;
      return transportersApi.updateVehicle(targetTransporterId, vehicleId, data);
    },
    onSuccess: (_, variables) => {
      const tid = variables?.transporterId || variables?.data?.transporter_id || defaultTransporterId;
      if (tid) {
        queryClient.invalidateQueries({ queryKey: ['transporter-vehicles', tid] });
        queryClient.invalidateQueries({ queryKey: ['transporters', tid] });
      }
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles-all'] });
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
    },
  });
};

export const useDeleteVehicle = (defaultTransporterId) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (arg) => {
      const vehicleId = typeof arg === 'object' ? arg.vehicleId : arg;
      const targetTransporterId = (typeof arg === 'object' ? arg.transporterId : null) || defaultTransporterId;
      return transportersApi.deleteVehicle(targetTransporterId, vehicleId);
    },
    onSuccess: (_, variables) => {
      const tid = (typeof variables === 'object' ? variables?.transporterId : null) || defaultTransporterId;
      if (tid) {
        queryClient.invalidateQueries({ queryKey: ['transporter-vehicles', tid] });
        queryClient.invalidateQueries({ queryKey: ['transporters', tid] });
      }
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transporter-vehicles-all'] });
      queryClient.invalidateQueries({ queryKey: ['transporters'] });
    },
  });
};
