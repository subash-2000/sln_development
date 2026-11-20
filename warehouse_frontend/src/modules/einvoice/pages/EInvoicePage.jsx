import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileCheck2, Plus, Settings2, History, Save, Send, Truck, Ban } from 'lucide-react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import { einvoiceApi } from '../api/einvoice.api';
import { invoicingApi } from '../../invoicing/api/invoicing.api';
import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { unwrapList } from '../../../services/api/unwrap';

const emptyConfig = {
  enabled: false,
  ewaybill_enabled: false,
  auto_generate: false,
  environment: 'sandbox',
  provider: 'mygstcafe',
  gstin: '',
  asp_gstin: '',
  api_username: '',
  api_password: '',
  customer_id: '',
  api_id: '',
  api_secret: '',
  client_id: '',
  client_secret: '',
  auth_token: '',
};
const tabs = [
  ['documents', 'Documents', FileCheck2],
  ['prepare', 'Prepare', Plus],
  ['configuration', 'Configuration', Settings2],
  ['logs', 'API Logs', History],
];

const Toggle = ({ label, checked, onChange }) => (
  <label className="flex items-center gap-3 text-sm font-medium text-gray-700">
    <input
      type="checkbox"
      className="h-4 w-4"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
    />
    {label}
  </label>
);
const Select = ({ label, value, onChange, children }) => (
  <label className="space-y-1.5 text-sm font-medium text-gray-700">
    <span>{label}</span>
    <select
      className="w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {children}
    </select>
  </label>
);
const statusClass = (value) =>
  value?.includes('CANCELLED')
    ? 'bg-red-50 text-red-700'
    : value === 'FAILED'
      ? 'bg-amber-50 text-amber-700'
      : value === 'DRAFT'
        ? 'bg-gray-100 text-gray-700'
        : 'bg-green-50 text-green-700';

export default function EInvoicePage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('documents');
  const [config, setConfig] = useState(emptyConfig);
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState({
    source: 'invoice',
    invoice_id: '',
    dispatch_order_id: '',
    document_type: 'E_INVOICE',
    distance_km: '',
    transporter_id: '',
    transport_mode: '1',
    vehicle_number: '',
    vehicle_type: 'R',
  });
  const configuration = useQuery({
    queryKey: ['einvoice-configuration'],
    queryFn: einvoiceApi.configuration,
  });
  const documents = useQuery({
    queryKey: ['einvoice-documents'],
    queryFn: () => einvoiceApi.documents({ page: 1, page_size: 100 }),
  });
  const logs = useQuery({
    queryKey: ['einvoice-logs'],
    queryFn: () => einvoiceApi.logs({ page: 1, page_size: 100 }),
    enabled: tab === 'logs',
  });
  const invoices = useQuery({
    queryKey: ['einvoice-source-invoices'],
    queryFn: () => invoicingApi.list({ page: 1, page_size: 100 }),
    enabled: tab === 'prepare',
  });
  const dispatches = useQuery({
    queryKey: ['einvoice-source-dispatches'],
    queryFn: async () =>
      unwrapList(
        await apiClient.get(ENDPOINTS.LOGISTICS.DISPATCH, { params: { page: 1, page_size: 100 } })
      ),
    enabled: tab === 'prepare',
  });
  useEffect(() => {
    if (configuration.data) setConfig({ ...emptyConfig, ...configuration.data });
  }, [configuration.data]);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['einvoice-documents'] });
    queryClient.invalidateQueries({ queryKey: ['einvoice-logs'] });
  };
  const action = useMutation({
    mutationFn: ({ method, id, payload }) => einvoiceApi[method](id, payload),
    onSuccess: () => {
      setNotice('Operation completed successfully.');
      refresh();
    },
    onError: (e) => setNotice(e?.response?.data?.message || e.message),
  });
  const save = useMutation({
    mutationFn: einvoiceApi.saveConfiguration,
    onSuccess: (data) => {
      setConfig({ ...emptyConfig, ...data });
      setNotice('Configuration saved. Secret values remain write-only.');
      queryClient.invalidateQueries({ queryKey: ['einvoice-configuration'] });
    },
    onError: (e) => setNotice(e?.response?.data?.message || e.message),
  });
  const create = useMutation({
    mutationFn: einvoiceApi.createDocument,
    onSuccess: () => {
      setNotice('Document prepared. Review the JSON before generation.');
      setTab('documents');
      refresh();
    },
    onError: (e) => setNotice(e?.response?.data?.message || e.message),
  });

  const submitDraft = () =>
    create.mutate({
      document_type: draft.document_type,
      invoice_id: draft.source === 'invoice' ? draft.invoice_id : null,
      dispatch_order_id: draft.source === 'dispatch' ? draft.dispatch_order_id : null,
      distance_km: draft.distance_km ? Number(draft.distance_km) : null,
      transporter_id: draft.transporter_id || null,
      transport_mode: draft.transport_mode,
      vehicle_number: draft.vehicle_number || null,
      vehicle_type: draft.vehicle_type,
    });
  const cancel = (method, id) => {
    const remarks = window.prompt('Cancellation remarks');
    if (remarks) action.mutate({ method, id, payload: { reason: '1', remarks } });
  };

  return (
    <div className="w-full space-y-6 pb-12">
      <PageHeader
        title="E-Invoice & E-Way Bill"
        description="Generate IRNs and e-way bills without changing the existing invoicing or logistics workflows."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'E-Invoice & E-Way Bill' },
        ]}
      />
      {notice && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {notice}
        </div>
      )}
      <div className="flex gap-2 border-b border-gray-200">
        {tabs.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 ${tab === id ? 'border-primary-600 text-primary-700' : 'border-transparent text-gray-500'}`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'documents' && (
        <Card>
          <Card.Header>
            <Card.Title>Statutory Documents</Card.Title>
          </Card.Header>
          <Card.Body className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-3">Document</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>IRN</th>
                  <th>E-Way Bill</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {(documents.data?.items || []).map((doc) => (
                  <tr key={doc.id} className="border-b last:border-0">
                    <td className="py-3 font-medium">{doc.document_number}</td>
                    <td>{doc.document_type}</td>
                    <td>
                      <span className={`rounded-full px-2 py-1 text-xs ${statusClass(doc.status)}`}>
                        {doc.status}
                      </span>
                    </td>
                    <td className="max-w-48 truncate" title={doc.irn}>
                      {doc.irn || '—'}
                    </td>
                    <td>{doc.ewaybill_number || '—'}</td>
                    <td>
                      <div className="flex flex-wrap gap-2">
                        {doc.status === 'DRAFT' && (
                          <Button
                            size="sm"
                            onClick={() =>
                              action.mutate({
                                method:
                                  doc.document_type === 'EWAY_BILL'
                                    ? 'generateEwaybill'
                                    : 'generateIrn',
                                id: doc.id,
                              })
                            }
                            leftIcon={<Send size={14} />}
                          >
                            {doc.document_type === 'EWAY_BILL'
                              ? 'Generate E-Way Bill'
                              : 'Generate IRN'}
                          </Button>
                        )}
                        {doc.irn && !doc.ewaybill_number && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              action.mutate({ method: 'generateEwaybill', id: doc.id })
                            }
                            leftIcon={<Truck size={14} />}
                          >
                            E-Way Bill
                          </Button>
                        )}
                        {doc.irn && !doc.status.includes('CANCELLED') && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => cancel('cancelIrn', doc.id)}
                            leftIcon={<Ban size={14} />}
                          >
                            Cancel IRN
                          </Button>
                        )}
                        {doc.ewaybill_number && !doc.status.includes('CANCELLED') && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => cancel('cancelEwaybill', doc.id)}
                          >
                            Cancel EWB
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!documents.isLoading && !documents.data?.items?.length && (
              <p className="py-10 text-center text-gray-500">
                No statutory documents prepared yet.
              </p>
            )}
          </Card.Body>
        </Card>
      )}

      {tab === 'prepare' && (
        <Card>
          <Card.Header>
            <Card.Title>Prepare New Document</Card.Title>
          </Card.Header>
          <Card.Body className="space-y-5">
            <div className="grid md:grid-cols-2 gap-5">
              <Select
                label="Source"
                value={draft.source}
                onChange={(v) => setDraft({ ...draft, source: v })}
              >
                <option value="invoice">Existing Invoice</option>
                <option value="dispatch">Existing Dispatch / Challan</option>
              </Select>
              <Select
                label="Document Type"
                value={draft.document_type}
                onChange={(v) => setDraft({ ...draft, document_type: v })}
              >
                <option value="E_INVOICE">E-Invoice</option>
                <option value="EWAY_BILL">Direct E-Way Bill / Challan</option>
              </Select>
            </div>
            {draft.source === 'invoice' ? (
              <Select
                label="Invoice"
                value={draft.invoice_id}
                onChange={(v) => setDraft({ ...draft, invoice_id: v })}
              >
                <option value="">Select invoice</option>
                {(invoices.data?.items || []).map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.invoice_number} — {x.customer_name || 'No customer'} — ₹{x.total_amount}
                  </option>
                ))}
              </Select>
            ) : (
              <Select
                label="Dispatch / Challan"
                value={draft.dispatch_order_id}
                onChange={(v) => setDraft({ ...draft, dispatch_order_id: v })}
              >
                <option value="">Select dispatch</option>
                {(dispatches.data?.items || []).map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.dispatch_number} — {x.customer_name || x.vendor_name || 'Transfer'}
                  </option>
                ))}
              </Select>
            )}
            <div className="grid md:grid-cols-3 gap-5">
              <Input
                label="Distance (km)"
                type="number"
                value={draft.distance_km}
                onChange={(e) => setDraft({ ...draft, distance_km: e.target.value })}
              />
              <Input
                label="Transporter GSTIN"
                value={draft.transporter_id}
                onChange={(e) => setDraft({ ...draft, transporter_id: e.target.value })}
              />
              <Input
                label="Vehicle Number"
                value={draft.vehicle_number}
                onChange={(e) => setDraft({ ...draft, vehicle_number: e.target.value })}
              />
            </div>
            <Button
              onClick={submitDraft}
              isLoading={create.isPending}
              disabled={draft.source === 'invoice' ? !draft.invoice_id : !draft.dispatch_order_id}
              leftIcon={<Plus size={16} />}
            >
              Prepare Document
            </Button>
          </Card.Body>
        </Card>
      )}

      {tab === 'configuration' && (
        <Card>
          <Card.Header>
            <Card.Title>Company API Configuration</Card.Title>
            <p className="text-xs text-gray-500 mt-1">
              Credentials apply only to the active company. Saved secrets are never returned to the
              browser.
            </p>
          </Card.Header>
          <Card.Body className="space-y-6">
            <div className="flex flex-wrap gap-6">
              <Toggle
                label="Enable E-Invoice"
                checked={config.enabled}
                onChange={(v) => setConfig({ ...config, enabled: v })}
              />
              <Toggle
                label="Enable E-Way Bill"
                checked={config.ewaybill_enabled}
                onChange={(v) => setConfig({ ...config, ewaybill_enabled: v })}
              />
              <Toggle
                label="Auto-generate"
                checked={config.auto_generate}
                onChange={(v) => setConfig({ ...config, auto_generate: v })}
              />
            </div>
            <div className="grid md:grid-cols-2 gap-5">
              <Select
                label="Provider"
                value={config.provider}
                onChange={(v) => setConfig({ ...config, provider: v })}
              >
                <option value="mygstcafe">MyGSTCafe (Pinnacle)</option>
                <option value="nic_direct">NIC Direct</option>
              </Select>
              <Select
                label="Environment"
                value={config.environment}
                onChange={(v) => setConfig({ ...config, environment: v })}
              >
                <option value="sandbox">Sandbox</option>
                <option value="production">Production</option>
              </Select>
              <Input
                label="Client GSTIN"
                value={config.gstin || ''}
                onChange={(e) => setConfig({ ...config, gstin: e.target.value.toUpperCase() })}
              />
              <Input
                label="IRP Username"
                value={config.api_username || ''}
                onChange={(e) => setConfig({ ...config, api_username: e.target.value })}
              />
              <Input
                label="IRP Password"
                type="password"
                placeholder={config.has_api_password ? 'Saved — enter only to replace' : ''}
                value={config.api_password || ''}
                onChange={(e) => setConfig({ ...config, api_password: e.target.value })}
              />
              {config.provider === 'mygstcafe' ? (
                <>
                  <Input
                    label="ASP GSTIN"
                    value={config.asp_gstin || ''}
                    onChange={(e) =>
                      setConfig({ ...config, asp_gstin: e.target.value.toUpperCase() })
                    }
                  />
                  <Input
                    label="Customer ID"
                    value={config.customer_id || ''}
                    onChange={(e) => setConfig({ ...config, customer_id: e.target.value })}
                  />
                  <Input
                    label="API ID"
                    value={config.api_id || ''}
                    onChange={(e) => setConfig({ ...config, api_id: e.target.value })}
                  />
                  <Input
                    label="API Secret"
                    type="password"
                    placeholder={config.has_api_secret ? 'Saved — enter only to replace' : ''}
                    value={config.api_secret || ''}
                    onChange={(e) => setConfig({ ...config, api_secret: e.target.value })}
                  />
                </>
              ) : (
                <>
                  <Input
                    label="NIC Client ID"
                    value={config.client_id || ''}
                    onChange={(e) => setConfig({ ...config, client_id: e.target.value })}
                  />
                  <Input
                    label="NIC Client Secret"
                    type="password"
                    placeholder={config.has_client_secret ? 'Saved — enter only to replace' : ''}
                    value={config.client_secret || ''}
                    onChange={(e) => setConfig({ ...config, client_secret: e.target.value })}
                  />
                  <Input
                    label="NIC Auth Token"
                    type="password"
                    placeholder={config.has_auth_token ? 'Saved — enter only to replace' : ''}
                    value={config.auth_token || ''}
                    onChange={(e) => setConfig({ ...config, auth_token: e.target.value })}
                  />
                </>
              )}
            </div>
            <Button
              onClick={() => save.mutate(config)}
              isLoading={save.isPending}
              leftIcon={<Save size={16} />}
            >
              Save Configuration
            </Button>
          </Card.Body>
        </Card>
      )}

      {tab === 'logs' && (
        <Card>
          <Card.Header>
            <Card.Title>API Audit Log</Card.Title>
          </Card.Header>
          <Card.Body className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-3">Time</th>
                  <th>Operation</th>
                  <th>HTTP</th>
                  <th>Result</th>
                  <th>Duration</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {(logs.data?.items || []).map((log) => (
                  <tr key={log.id} className="border-b last:border-0">
                    <td className="py-3">{new Date(log.created_at).toLocaleString()}</td>
                    <td>{log.operation}</td>
                    <td>{log.http_status || '—'}</td>
                    <td className={log.success ? 'text-green-700' : 'text-red-700'}>
                      {log.success ? 'Success' : 'Failed'}
                    </td>
                    <td>{log.duration_ms ? `${log.duration_ms} ms` : '—'}</td>
                    <td className="max-w-xs truncate" title={log.error_message}>
                      {log.error_message || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}
