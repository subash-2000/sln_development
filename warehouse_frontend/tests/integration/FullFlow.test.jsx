import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from '../../src/pages/auth/LoginPage';
import UserCreatePage from '../../src/modules/users/pages/UserCreatePage';
import VendorCreatePage from '../../src/modules/vendors/pages/VendorCreatePage';
import CustomerCreatePage from '../../src/modules/customers/pages/CustomerCreatePage';
import ProductCreatePage from '../../src/modules/products/pages/ProductCreatePage';
import WarehouseCreatePage from '../../src/modules/warehouses/pages/WarehouseCreatePage';
import LocationCreatePage from '../../src/modules/locations/pages/LocationCreatePage';
import LogisticsInwardCreatePage from '../../src/modules/logistics/pages/LogisticsInwardCreatePage';
import apiClient from '../../src/services/api/client';

// Mock the API client
vi.mock('../../src/services/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { baseURL: '' },
  },
}));

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

describe('Full Frontend Flow Integration Tests', () => {
  let queryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  describe('Login Flow', () => {
    it('should login successfully with valid credentials', async () => {
      // Mock successful login response
      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { access_token: 'fake-access-token', refresh_token: 'fake-refresh-token' },
      });
      // Mock getCurrentUser response
      apiClient.get.mockResolvedValueOnce({
        success: true,
        data: { id: 'user-1', username: 'admin', full_name: 'Administrator', permissions: ['*'] },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <LoginPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'admin' } });
      fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password123' } });
      
      const loginButton = screen.getByRole('button', { name: /Sign In/i });
      fireEvent.click(loginButton);

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
          username_or_email: 'admin',
          password: 'password123',
        });
      });
    });

    it('should show error message on login failure', async () => {
      // Mock an error that looks like ApiError
      apiClient.post.mockRejectedValueOnce({
        message: 'Invalid credentials',
        code: 'AUTH_FAILED',
        status: 401,
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <LoginPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'wrong' } });
      fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'wrong' } });
      fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

      await waitFor(() => {
        expect(screen.getByText(/Login Failed/i)).toBeInTheDocument();
        expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
      });
    });
  });

  describe('User Creation Flow', () => {
    it('should create a user successfully', async () => {
      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'new-user-1', username: 'johndoe', email: 'john@example.com', roles: ['WAREHOUSE_MANAGER'] },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <UserCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'johndoe' } });
      fireEvent.change(screen.getByLabelText(/Email Address/i), { target: { value: 'john@example.com' } });
      fireEvent.change(screen.getByLabelText(/Full Name/i), { target: { value: 'John Doe' } });
      fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'secret123' } });
      
      // Select role
      fireEvent.change(screen.getByLabelText(/Role/i), { target: { value: 'role_1' } });

      // Select company
      fireEvent.click(screen.getByLabelText(/Company Alpha/i));

      fireEvent.click(screen.getByRole('button', { name: /Create User/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/users', expect.objectContaining({
          username: 'johndoe',
          email: 'john@example.com',
        }));
      });
    });
  });

  describe('Vendor Creation Flow', () => {
    it('should create a vendor successfully', async () => {
      apiClient.get.mockImplementation((url) => {
        if (url.includes('/suppliers')) {
          return Promise.resolve({
            success: true,
            data: [],
          });
        }
        return Promise.resolve({ success: true, data: [] });
      });

      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'vendor-1', code: 'VND001', name: 'Acme Corp' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <VendorCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByLabelText(/Vendor Code/i), { target: { value: 'VND001' } });
      fireEvent.change(screen.getByLabelText(/Vendor Name/i), { target: { value: 'Acme Corp' } });
      fireEvent.change(screen.getByLabelText(/GSTIN/i), { target: { value: '29ABCDE1234F1Z5' } });
      fireEvent.change(screen.getByLabelText(/Phone Number/i), { target: { value: '9876543210' } });
      fireEvent.change(screen.getByLabelText(/^Address/i), { target: { value: '123 Industrial Area, Bangalore' } });

      fireEvent.click(screen.getByRole('button', { name: /Create Vendor/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/suppliers', expect.objectContaining({
          code: 'VND001',
          name: 'Acme Corp',
        }));
      });
    });
  });

  describe('Customer Creation Flow', () => {
    it('should create a customer successfully', async () => {
      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'cust-1', code: 'CUST001', name: 'Global Traders' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <CustomerCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByLabelText(/Customer Code/i), { target: { value: 'CUST001' } });
      fireEvent.change(screen.getByLabelText(/Customer Name/i), { target: { value: 'Global Traders' } });

      fireEvent.click(screen.getByRole('button', { name: /Create Customer/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/customers', expect.objectContaining({
          code: 'CUST001',
          name: 'Global Traders',
        }));
      });
    });
  });

  describe('Product Creation Flow', () => {
    it('should create a product successfully', async () => {
      // Robust mocking
      apiClient.get.mockImplementation((url) => {
        if (url.includes('/product-categories')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'cat-1', name: 'Electronics' }],
          });
        }
        if (url.includes('/uoms')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'uom-1', name: 'Pieces', code: 'PCS' }],
          });
        }
        if (url.includes('/auth/me')) {
          return Promise.resolve({
            success: true,
            data: { id: 'admin-1', username: 'admin', full_name: 'Admin', permissions: ['*'] }
          });
        }
        return Promise.resolve({ success: true, data: [] });
      });
      
      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'prod-1', sku: 'SKU001', name: 'Gadget' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ProductCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Wait for categories to load
      await waitFor(() => {
        const categorySelect = screen.getByLabelText(/Category/i);
        expect(categorySelect.querySelectorAll('option').length).toBeGreaterThan(1);
      });

      // Wait for UOMs to load
      await waitFor(() => {
        const uomSelect = screen.getByLabelText(/UOM/i);
        expect(uomSelect.querySelectorAll('option').length).toBeGreaterThan(1);
      });

      fireEvent.change(screen.getByLabelText(/SKU/i), { target: { value: 'SKU001' } });
      fireEvent.change(screen.getByLabelText(/Product Name/i), { target: { value: 'Gadget' } });
      fireEvent.change(screen.getByLabelText(/Category/i), { target: { value: 'cat-1' } });
      fireEvent.change(screen.getByLabelText(/UOM/i), { target: { value: 'uom-1' } });

      fireEvent.click(screen.getByRole('button', { name: /Create Product/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/products', expect.objectContaining({
          sku: 'SKU001',
          name: 'Gadget',
          category_id: 'cat-1',
          uom_id: 'uom-1',
        }));
      });
    });
  });

  describe('Warehouse Creation Flow', () => {
    it('should create a warehouse successfully', async () => {
      // Mock companies and branches
      apiClient.get.mockImplementation((url) => {
        if (url.includes('/companies')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'cmp-1', name: 'Company Alpha' }],
          });
        }
        if (url.includes('/branches')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'br-1', name: 'Branch A1', company_id: 'cmp-1' }],
          });
        }
        return Promise.resolve({ success: true, data: [] });
      });

      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'wh-1', code: 'WH001', name: 'Main Warehouse' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <WarehouseCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Wait for selects to populate
      await waitFor(() => {
        const companySelect = screen.getByLabelText(/Company/i);
        expect(companySelect.querySelectorAll('option').length).toBeGreaterThan(1);
      });

      fireEvent.change(screen.getByLabelText(/Company/i), { target: { value: 'cmp-1' } });

      // Wait for branch to load after company selection
      await waitFor(() => {
        const branchSelect = screen.getByLabelText(/Branch/i);
        expect(branchSelect.querySelectorAll('option').length).toBeGreaterThan(1);
      });

      fireEvent.change(screen.getByLabelText(/Branch/i), { target: { value: 'br-1' } });
      fireEvent.change(screen.getByLabelText(/Warehouse Code/i), { target: { value: 'WH001' } });
      fireEvent.change(screen.getByLabelText(/Warehouse Name/i), { target: { value: 'Main Warehouse' } });
      fireEvent.change(screen.getByLabelText(/City/i), { target: { value: 'Mumbai' } });
      fireEvent.change(screen.getByLabelText(/State/i), { target: { value: 'Maharashtra' } });

      fireEvent.click(screen.getByRole('button', { name: /Create Warehouse/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/warehouses', expect.objectContaining({
          code: 'WH001',
          name: 'Main Warehouse',
          company_id: 'cmp-1',
          branch_id: 'br-1',
        }));
      });
    });
  });

  describe('Location Creation Flow', () => {
    it('should create a location successfully', async () => {
      // Mock warehouses
      apiClient.get.mockImplementation((url) => {
        if (url.includes('/warehouses')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'wh-1', code: 'WH001', name: 'Main Warehouse' }],
          });
        }
        return Promise.resolve({ success: true, data: [] });
      });

      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'loc-1', code: 'LOC001', name: 'Bin A1' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <LocationCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Wait for warehouse to load
      await waitFor(() => {
        const warehouseSelect = screen.getByLabelText(/Warehouse/i);
        expect(warehouseSelect.querySelectorAll('option').length).toBeGreaterThan(1);
      });

      fireEvent.change(screen.getByLabelText(/Warehouse/i), { target: { value: 'wh-1' } });
      fireEvent.change(screen.getByLabelText(/Location Code/i), { target: { value: 'LOC001' } });
      fireEvent.change(screen.getByLabelText(/Location Name/i), { target: { value: 'Bin A1' } });
      fireEvent.change(screen.getByLabelText(/Location Type/i), { target: { value: 'STORAGE' } });

      fireEvent.click(screen.getByRole('button', { name: /Create Location/i }));

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/locations', expect.objectContaining({
          code: 'LOC001',
          name: 'Bin A1',
          warehouse_id: 'wh-1',
        }));
      });
    });
  });

  describe('Logistics Inward Flow', () => {
    it('should create an inward transaction successfully', async () => {
      // Mock warehouses, vendors, products, uoms
      apiClient.get.mockImplementation((url) => {
        if (url.includes('/warehouses')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'wh-1', name: 'Main Warehouse' }],
          });
        }
        if (url.includes('/suppliers')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'v-1', name: 'Acme Supplies' }],
          });
        }
        if (url.includes('/product-categories')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'cat-1', name: 'Electronics' }],
          });
        }
        if (url.includes('/uoms')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'u-1', name: 'Pieces', code: 'PCS' }],
          });
        }
        if (url.includes('/products')) {
          return Promise.resolve({
            success: true,
            data: [{ id: 'p-1', name: 'Gadget', sku: 'SKU001' }],
          });
        }
        return Promise.resolve({ success: true, data: [] });
      });

      apiClient.post.mockResolvedValueOnce({
        success: true,
        data: { id: 'inw-1', transaction_number: 'INW-2026-001' },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <LogisticsInwardCreatePage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByLabelText(/Warehouse/i).querySelectorAll('option').length).toBeGreaterThan(1);
      });

      fireEvent.change(screen.getByLabelText(/Warehouse/i), { target: { value: 'wh-1' } });
      fireEvent.change(screen.getByLabelText(/Vendor/i), { target: { value: 'v-1' } });
      fireEvent.change(screen.getByLabelText(/Reference Number/i), { target: { value: 'PO-100' } });

      // Item selection
      const productSelect = screen.getByLabelText(/Product/i);
      fireEvent.change(productSelect, { target: { value: 'p-1' } });
      
      const quantityInput = screen.getByLabelText(/Quantity/i);
      fireEvent.change(quantityInput, { target: { value: '10' } });
      
      const uomSelect = screen.getByLabelText(/UOM/i);
      fireEvent.change(uomSelect, { target: { value: 'u-1' } });

      const submitButton = screen.getByRole('button', { name: /Post Inward/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/logistics/inward', expect.objectContaining({
          warehouse_id: 'wh-1',
          vendor_id: 'v-1',
          items: expect.arrayContaining([
            expect.objectContaining({ product_id: 'p-1', quantity: 10 })
          ])
        }));
      }, { timeout: 3000 });
    });
  });
});
