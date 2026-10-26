import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import SystemSettingsPage from '../../src/pages/settings/SystemSettingsPage';

describe('SystemSettingsPage Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should render System Settings with tabs and General settings active by default', () => {
    render(
      <MemoryRouter>
        <SystemSettingsPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: 'System Settings' })).toBeInTheDocument();
    expect(screen.getByText('General Configuration')).toBeInTheDocument();
    expect(screen.getByLabelText(/Application Name/i)).toHaveValue('SLN WMS');
    expect(screen.getByLabelText(/Tenant \/ Company Name/i)).toHaveValue('SLN Warehouse Solutions Ltd');
  });

  it('should switch between tabs and display corresponding settings', () => {
    render(
      <MemoryRouter>
        <SystemSettingsPage />
      </MemoryRouter>
    );

    // Switch to Warehouse & Operations tab
    fireEvent.click(screen.getByRole('button', { name: /Warehouse & Operations/i }));
    expect(screen.getByText('Warehouse & Operations Rules')).toBeInTheDocument();
    expect(screen.getByLabelText(/Default Valuation Method/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Auto SKU Prefix/i)).toHaveValue('SKU-');

    // Switch to Security & Access tab
    fireEvent.click(screen.getByRole('button', { name: /Security & Access/i }));
    expect(screen.getByText('Security & Access Control')).toBeInTheDocument();
    expect(screen.getByLabelText(/Session Timeout \(Minutes\)/i)).toBeInTheDocument();

    // Switch to Notifications tab
    fireEvent.click(screen.getByRole('button', { name: /Notifications/i }));
    expect(screen.getByText('Alerts & Notifications')).toBeInTheDocument();
    expect(screen.getByLabelText(/Low Stock Warning Threshold/i)).toBeInTheDocument();

    // Switch to Compliance & System tab
    fireEvent.click(screen.getByRole('button', { name: /Compliance & System/i }));
    expect(screen.getByText('Compliance & System Integration')).toBeInTheDocument();
    expect(screen.getByLabelText(/Default Interface Language/i)).toBeInTheDocument();
  });

  it('should update settings and save to localStorage with success alert', async () => {
    render(
      <MemoryRouter>
        <SystemSettingsPage />
      </MemoryRouter>
    );

    const appNameInput = screen.getByLabelText(/Application Name/i);
    fireEvent.change(appNameInput, { target: { value: 'Enterprise WMS Pro' } });
    expect(appNameInput).toHaveValue('Enterprise WMS Pro');

    const saveButtons = screen.getAllByRole('button', { name: /Save/i });
    fireEvent.click(saveButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByText(/System settings have been successfully saved/i)
      ).toBeInTheDocument();
    });

    const stored = JSON.parse(localStorage.getItem('wms_system_settings') || '{}');
    expect(stored.appName).toBe('Enterprise WMS Pro');
  });

  it('should toggle switch settings correctly', () => {
    render(
      <MemoryRouter>
        <SystemSettingsPage />
      </MemoryRouter>
    );

    // Go to Operations
    fireEvent.click(screen.getByRole('button', { name: /Warehouse & Operations/i }));
    
    const multiBinSwitch = screen.getByRole('switch', { name: /Multi-Bin Allocation per SKU/i });
    expect(multiBinSwitch).toHaveAttribute('aria-checked', 'true');

    fireEvent.click(multiBinSwitch);
    expect(multiBinSwitch).toHaveAttribute('aria-checked', 'false');
  });
});
