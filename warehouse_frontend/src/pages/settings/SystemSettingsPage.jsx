import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Warehouse,
  Shield,
  Bell,
  Globe,
  Save,
  RotateCcw,
  CheckCircle2,
  Building,
  Clock,
  Lock,
  Mail,
  FileText,
} from 'lucide-react';
import PageHeader from '../../components/common/PageHeader';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';

const SETTINGS_STORAGE_KEY = 'wms_system_settings';

const DEFAULT_SETTINGS = {
  // General
  appName: 'SLN WMS',
  tenantName: 'SLN Warehouse Solutions Ltd',
  environment: 'Production',
  timezone: 'Asia/Kolkata (IST, UTC+5:30)',
  dateFormat: 'DD/MM/YYYY',
  currency: 'INR',
  supportEmail: 'support@slnwms.com',

  // Operations
  inventoryValuation: 'FIFO',
  skuPrefix: 'SKU-',
  barcodePrefix: 'BAR-',
  multiBinAllocation: true,
  enforceCapacityLimits: true,
  autoCloseInward: true,
  defaultPaymentTermsDays: 30,

  // Security
  sessionTimeoutMinutes: 60,
  maxLoginAttempts: 5,
  passwordExpiryDays: 90,
  requireMfaForAdmins: true,
  restrictConcurrentSessions: true,

  // Notifications
  lowStockThreshold: 50,
  emailOnDiscrepancy: true,
  dailyDigestSummary: true,
  adminAlertEmail: 'admin@slnwms.com',

  // Compliance & System
  defaultLanguage: 'en',
  measurementSystem: 'metric',
  enableGstEInvoicing: true,
  auditLogRetentionDays: 365,
};

const ToggleSwitch = ({ id, label, description, checked, onChange }) => (
  <div className="flex items-start justify-between py-3 border-b border-gray-100 last:border-0">
    <div className="space-y-0.5 pr-4">
      <label htmlFor={id} className="text-sm font-medium text-gray-900 cursor-pointer">
        {label}
      </label>
      {description && <p className="text-xs text-gray-500 leading-relaxed">{description}</p>}
    </div>
    <button
      type="button"
      id={id}
      role="switch"
      aria-label={label}
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
        checked ? 'bg-primary-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  </div>
);

const SystemSettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
      }
    } catch (e) {
      console.error('Failed to load settings from storage', e);
    }
  }, []);

  const handleChange = (key, value) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }));
    setIsSaved(false);
  };

  const handleSave = (e) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setTimeout(() => {
      try {
        localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
        setIsSaved(true);
        setTimeout(() => setIsSaved(false), 4000);
      } catch (err) {
        console.error('Failed to save settings', err);
      } finally {
        setIsSaving(false);
      }
    }, 400);
  };

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset all settings to defaults?')) {
      setSettings(DEFAULT_SETTINGS);
      localStorage.removeItem(SETTINGS_STORAGE_KEY);
      setIsSaved(false);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Sliders },
    { id: 'operations', label: 'Warehouse & Operations', icon: Warehouse },
    { id: 'security', label: 'Security & Access', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'compliance', label: 'Compliance & System', icon: Globe },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <PageHeader
        title="System Settings"
        description="Configure system parameters, operational business rules, security policies, and integrations."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'System' },
          { label: 'System Settings' },
        ]}
        actions={
          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="secondary"
              onClick={handleReset}
              leftIcon={<RotateCcw className="w-4 h-4" />}
            >
              Reset Defaults
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleSave}
              isLoading={isSaving}
              leftIcon={<Save className="w-4 h-4" />}
            >
              Save Changes
            </Button>
          </div>
        }
      />

      {isSaved && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl flex items-center space-x-3 text-green-800 transition-all duration-300">
          <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
          <p className="text-sm font-medium">
            System settings have been successfully saved and updated across all sessions.
          </p>
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-6">
        {/* Navigation Tabs */}
        <div className="w-full md:w-64 flex-shrink-0">
          <Card className="p-2 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 font-semibold shadow-xs'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 flex-shrink-0 ${
                      isActive ? 'text-primary-600' : 'text-gray-400'
                    }`}
                  />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </Card>
        </div>

        {/* Tab Content Panels */}
        <div className="flex-1">
          <form onSubmit={handleSave}>
            {/* General Tab */}
            {activeTab === 'general' && (
              <Card>
                <Card.Header>
                  <Card.Title>General Configuration</Card.Title>
                  <p className="text-xs text-gray-500 mt-1">
                    Core identity, enterprise branding, and global date/currency settings.
                  </p>
                </Card.Header>
                <Card.Body className="space-y-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <Input
                      id="appName"
                      name="appName"
                      label="Application Name"
                      value={settings.appName}
                      onChange={(e) => handleChange('appName', e.target.value)}
                      placeholder="SLN WMS"
                      isRequired
                    />
                    <Input
                      id="tenantName"
                      name="tenantName"
                      label="Tenant / Company Name"
                      value={settings.tenantName}
                      onChange={(e) => handleChange('tenantName', e.target.value)}
                      placeholder="Enterprise Solutions Ltd"
                      isRequired
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div className="space-y-1.5">
                      <label htmlFor="environment" className="text-sm font-medium text-gray-700">
                        System Environment
                      </label>
                      <select
                        id="environment"
                        name="environment"
                        value={settings.environment}
                        onChange={(e) => handleChange('environment', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="Production">Production</option>
                        <option value="Staging">Staging</option>
                        <option value="Sandbox">Sandbox / Test</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label htmlFor="timezone" className="text-sm font-medium text-gray-700">
                        System Timezone
                      </label>
                      <select
                        id="timezone"
                        name="timezone"
                        value={settings.timezone}
                        onChange={(e) => handleChange('timezone', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="Asia/Kolkata (IST, UTC+5:30)">
                          Asia/Kolkata (IST, UTC+5:30)
                        </option>
                        <option value="UTC (GMT+0:00)">UTC (GMT+0:00)</option>
                        <option value="America/New_York (EST, UTC-5:00)">
                          America/New_York (EST, UTC-5:00)
                        </option>
                        <option value="Europe/London (GMT, UTC+0:00)">
                          Europe/London (GMT, UTC+0:00)
                        </option>
                        <option value="Asia/Singapore (SGT, UTC+8:00)">
                          Asia/Singapore (SGT, UTC+8:00)
                        </option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="space-y-1.5">
                      <label htmlFor="dateFormat" className="text-sm font-medium text-gray-700">
                        Date Display Format
                      </label>
                      <select
                        id="dateFormat"
                        name="dateFormat"
                        value={settings.dateFormat}
                        onChange={(e) => handleChange('dateFormat', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="DD/MM/YYYY">DD/MM/YYYY (e.g. 26/09/2026)</option>
                        <option value="MM/DD/YYYY">MM/DD/YYYY (e.g. 09/26/2026)</option>
                        <option value="YYYY-MM-DD">YYYY-MM-DD (ISO standard)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label htmlFor="currency" className="text-sm font-medium text-gray-700">
                        Default Currency
                      </label>
                      <select
                        id="currency"
                        name="currency"
                        value={settings.currency}
                        onChange={(e) => handleChange('currency', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="INR">INR (₹ - Indian Rupee)</option>
                        <option value="USD">USD ($ - US Dollar)</option>
                        <option value="EUR">EUR (€ - Euro)</option>
                        <option value="GBP">GBP (£ - British Pound)</option>
                      </select>
                    </div>

                    <Input
                      id="supportEmail"
                      name="supportEmail"
                      label="Support Email"
                      type="email"
                      value={settings.supportEmail}
                      onChange={(e) => handleChange('supportEmail', e.target.value)}
                      placeholder="support@slnwms.com"
                    />
                  </div>
                </Card.Body>
                <Card.Footer className="flex justify-end">
                  <Button type="submit" variant="primary" isLoading={isSaving}>
                    Save General Settings
                  </Button>
                </Card.Footer>
              </Card>
            )}

            {/* Warehouse & Operations Tab */}
            {activeTab === 'operations' && (
              <Card>
                <Card.Header>
                  <Card.Title>Warehouse & Operations Rules</Card.Title>
                  <p className="text-xs text-gray-500 mt-1">
                    Control how inventory valuation, numbering prefixes, and warehouse storage rules function.
                  </p>
                </Card.Header>
                <Card.Body className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="space-y-1.5">
                      <label
                        htmlFor="inventoryValuation"
                        className="text-sm font-medium text-gray-700"
                      >
                        Default Valuation Method
                      </label>
                      <select
                        id="inventoryValuation"
                        name="inventoryValuation"
                        value={settings.inventoryValuation}
                        onChange={(e) => handleChange('inventoryValuation', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="FIFO">FIFO (First In, First Out)</option>
                        <option value="LIFO">LIFO (Last In, First Out)</option>
                        <option value="WEIGHTED_AVG">Weighted Average Cost</option>
                      </select>
                    </div>

                    <Input
                      id="skuPrefix"
                      name="skuPrefix"
                      label="Auto SKU Prefix"
                      value={settings.skuPrefix}
                      onChange={(e) => handleChange('skuPrefix', e.target.value.toUpperCase())}
                      placeholder="SKU-"
                    />

                    <Input
                      id="barcodePrefix"
                      name="barcodePrefix"
                      label="Barcode Prefix"
                      value={settings.barcodePrefix}
                      onChange={(e) => handleChange('barcodePrefix', e.target.value.toUpperCase())}
                      placeholder="BAR-"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <Input
                      id="defaultPaymentTermsDays"
                      name="defaultPaymentTermsDays"
                      label="Default Payment Terms (Days)"
                      type="number"
                      min={0}
                      max={365}
                      value={settings.defaultPaymentTermsDays}
                      onChange={(e) =>
                        handleChange('defaultPaymentTermsDays', parseInt(e.target.value, 10) || 0)
                      }
                    />
                  </div>

                  <div className="pt-2">
                    <h4 className="text-sm font-semibold text-gray-800 mb-2">Operational Policies</h4>
                    <div className="divide-y divide-gray-100">
                      <ToggleSwitch
                        id="multiBinAllocation"
                        label="Multi-Bin Allocation per SKU"
                        description="Allow the same SKU to be stored across multiple storage locations and bins simultaneously."
                        checked={settings.multiBinAllocation}
                        onChange={(val) => handleChange('multiBinAllocation', val)}
                      />
                      <ToggleSwitch
                        id="enforceCapacityLimits"
                        label="Enforce Strict Location Capacity Limits"
                        description="Prevent putaway operations from exceeding defined bin volume and maximum weight limits."
                        checked={settings.enforceCapacityLimits}
                        onChange={(val) => handleChange('enforceCapacityLimits', val)}
                      />
                      <ToggleSwitch
                        id="autoCloseInward"
                        label="Auto-Close Inward GRN Orders"
                        description="Automatically mark Purchase Orders and Inward Receipts as complete when 100% quantity is received."
                        checked={settings.autoCloseInward}
                        onChange={(val) => handleChange('autoCloseInward', val)}
                      />
                    </div>
                  </div>
                </Card.Body>
                <Card.Footer className="flex justify-end">
                  <Button type="submit" variant="primary" isLoading={isSaving}>
                    Save Operations Settings
                  </Button>
                </Card.Footer>
              </Card>
            )}

            {/* Security & Access Tab */}
            {activeTab === 'security' && (
              <Card>
                <Card.Header>
                  <Card.Title>Security & Access Control</Card.Title>
                  <p className="text-xs text-gray-500 mt-1">
                    Authentication policies, session management, and credential protection.
                  </p>
                </Card.Header>
                <Card.Body className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <Input
                      id="sessionTimeoutMinutes"
                      name="sessionTimeoutMinutes"
                      label="Session Timeout (Minutes)"
                      type="number"
                      min={5}
                      max={1440}
                      value={settings.sessionTimeoutMinutes}
                      onChange={(e) =>
                        handleChange('sessionTimeoutMinutes', parseInt(e.target.value, 10) || 15)
                      }
                    />

                    <Input
                      id="maxLoginAttempts"
                      name="maxLoginAttempts"
                      label="Max Failed Login Attempts"
                      type="number"
                      min={3}
                      max={10}
                      value={settings.maxLoginAttempts}
                      onChange={(e) =>
                        handleChange('maxLoginAttempts', parseInt(e.target.value, 10) || 5)
                      }
                    />

                    <Input
                      id="passwordExpiryDays"
                      name="passwordExpiryDays"
                      label="Password Expiry (Days)"
                      type="number"
                      min={0}
                      max={365}
                      value={settings.passwordExpiryDays}
                      onChange={(e) =>
                        handleChange('passwordExpiryDays', parseInt(e.target.value, 10) || 0)
                      }
                    />
                  </div>

                  <div className="pt-2">
                    <h4 className="text-sm font-semibold text-gray-800 mb-2">Access Policies</h4>
                    <div className="divide-y divide-gray-100">
                      <ToggleSwitch
                        id="requireMfaForAdmins"
                        label="Require Two-Factor Authentication (2FA) for Admins"
                        description="Mandates an authenticator app code on login for Super Admin and Manager accounts."
                        checked={settings.requireMfaForAdmins}
                        onChange={(val) => handleChange('requireMfaForAdmins', val)}
                      />
                      <ToggleSwitch
                        id="restrictConcurrentSessions"
                        label="Restrict Concurrent Sessions"
                        description="Log out previous active sessions when a user signs in from a new browser or device."
                        checked={settings.restrictConcurrentSessions}
                        onChange={(val) => handleChange('restrictConcurrentSessions', val)}
                      />
                    </div>
                  </div>
                </Card.Body>
                <Card.Footer className="flex justify-end">
                  <Button type="submit" variant="primary" isLoading={isSaving}>
                    Save Security Settings
                  </Button>
                </Card.Footer>
              </Card>
            )}

            {/* Notifications Tab */}
            {activeTab === 'notifications' && (
              <Card>
                <Card.Header>
                  <Card.Title>Alerts & Notifications</Card.Title>
                  <p className="text-xs text-gray-500 mt-1">
                    Manage automated alert triggers and email notifications for warehouse personnel.
                  </p>
                </Card.Header>
                <Card.Body className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <Input
                      id="lowStockThreshold"
                      name="lowStockThreshold"
                      label="Low Stock Warning Threshold (Units)"
                      type="number"
                      min={1}
                      max={10000}
                      value={settings.lowStockThreshold}
                      onChange={(e) =>
                        handleChange('lowStockThreshold', parseInt(e.target.value, 10) || 10)
                      }
                    />

                    <Input
                      id="adminAlertEmail"
                      name="adminAlertEmail"
                      label="System Alert Recipient Email"
                      type="email"
                      value={settings.adminAlertEmail}
                      onChange={(e) => handleChange('adminAlertEmail', e.target.value)}
                      placeholder="admin@slnwms.com"
                    />
                  </div>

                  <div className="pt-2">
                    <h4 className="text-sm font-semibold text-gray-800 mb-2">Automated Notifications</h4>
                    <div className="divide-y divide-gray-100">
                      <ToggleSwitch
                        id="emailOnDiscrepancy"
                        label="Email Alert on Inward / Outward Discrepancy"
                        description="Automatically dispatch email to warehouse supervisor when received quantity mismatches invoice."
                        checked={settings.emailOnDiscrepancy}
                        onChange={(val) => handleChange('emailOnDiscrepancy', val)}
                      />
                      <ToggleSwitch
                        id="dailyDigestSummary"
                        label="Daily Warehouse Summary Digest"
                        description="Send daily morning email digest of opening stock, pending dispatches, and inward receipts."
                        checked={settings.dailyDigestSummary}
                        onChange={(val) => handleChange('dailyDigestSummary', val)}
                      />
                    </div>
                  </div>
                </Card.Body>
                <Card.Footer className="flex justify-end">
                  <Button type="submit" variant="primary" isLoading={isSaving}>
                    Save Notification Settings
                  </Button>
                </Card.Footer>
              </Card>
            )}

            {/* Compliance & System Tab */}
            {activeTab === 'compliance' && (
              <Card>
                <Card.Header>
                  <Card.Title>Compliance & System Integration</Card.Title>
                  <p className="text-xs text-gray-500 mt-1">
                    Regulatory compliance, tax e-Invoicing integration, and audit retention policies.
                  </p>
                </Card.Header>
                <Card.Body className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="space-y-1.5">
                      <label htmlFor="defaultLanguage" className="text-sm font-medium text-gray-700">
                        Default Interface Language
                      </label>
                      <select
                        id="defaultLanguage"
                        name="defaultLanguage"
                        value={settings.defaultLanguage}
                        onChange={(e) => handleChange('defaultLanguage', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="en">English (US/UK)</option>
                        <option value="hi">Hindi (हिंदी)</option>
                        <option value="kn">Kannada (ಕನ್ನಡ)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label htmlFor="measurementSystem" className="text-sm font-medium text-gray-700">
                        Measurement System
                      </label>
                      <select
                        id="measurementSystem"
                        name="measurementSystem"
                        value={settings.measurementSystem}
                        onChange={(e) => handleChange('measurementSystem', e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="metric">Metric (kg, m, cm, L)</option>
                        <option value="imperial">Imperial (lb, ft, in, gal)</option>
                      </select>
                    </div>

                    <Input
                      id="auditLogRetentionDays"
                      name="auditLogRetentionDays"
                      label="Audit Log Retention (Days)"
                      type="number"
                      min={30}
                      max={3650}
                      value={settings.auditLogRetentionDays}
                      onChange={(e) =>
                        handleChange('auditLogRetentionDays', parseInt(e.target.value, 10) || 365)
                      }
                    />
                  </div>

                  <div className="pt-2">
                    <h4 className="text-sm font-semibold text-gray-800 mb-2">Statutory Compliance</h4>
                    <div className="divide-y divide-gray-100">
                      <ToggleSwitch
                        id="enableGstEInvoicing"
                        label="Enable GST e-Invoicing Direct API"
                        description="Automatically generate IRN (Invoice Reference Number) and QR codes via NIC GST portal."
                        checked={settings.enableGstEInvoicing}
                        onChange={(val) => handleChange('enableGstEInvoicing', val)}
                      />
                    </div>
                  </div>
                </Card.Body>
                <Card.Footer className="flex justify-end">
                  <Button type="submit" variant="primary" isLoading={isSaving}>
                    Save Compliance Settings
                  </Button>
                </Card.Footer>
              </Card>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default SystemSettingsPage;
