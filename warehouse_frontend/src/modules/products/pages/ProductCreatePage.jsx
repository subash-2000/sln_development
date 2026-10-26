import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateProduct } from '../hooks/use-products';
import { useCompanies } from '../../companies/hooks/use-companies';
import ProductForm from '../components/ProductForm';
import Breadcrumb from '../../../components/navigation/Breadcrumb';

const ProductCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { data: companiesData } = useCompanies({ page_size: 10 });
  const { mutateAsync: createProduct, isPending } = useCreateProduct();
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSubmit = async (data) => {
    setErrorMsg(null);
    try {
      const companies = companiesData?.items || [];
      const resolvedCompanyId = data.company_id || companyContext || (companies.length > 0 ? companies[0].id : null) || null;

      await createProduct({
        ...data,
        company_id: resolvedCompanyId,
        category_id: data.category_id ? data.category_id : null,
        secondary_uom_id: data.secondary_uom_id ? data.secondary_uom_id : null,
        hsn_code: data.hsn_code ? data.hsn_code.trim() : null,
        part_number: data.part_number?.trim() || null,
        description: data.description ? data.description.trim() : null,
        barcode: data.barcode ? data.barcode.trim() : null,
        sku: data.sku ? data.sku.trim().toUpperCase() : '',
        name: data.name ? data.name.trim() : '',
        batch_number: data.batch_number?.trim() || null,
        heat_number: data.heat_number?.trim() || null,
        gauge_number: data.gauge_number?.trim() || null,
        mill_name: data.mill_name?.trim() || null,
        package_tracking_type: data.package_tracking_type || null,
        package_tracking_value: data.package_tracking_value?.trim() || null,
        packing_ratio: data.packing_ratio?.trim() || null,
        is_lot_tracked:
          data.is_lot_tracked
          || Boolean(
            data.batch_number?.trim()
              || data.heat_number?.trim()
              || data.gauge_number?.trim()
              || data.mill_name?.trim()
              || data.package_tracking_type
          ),
      });
      navigate('/products');
    } catch (error) {
      console.error('Failed to create product:', error);
      setErrorMsg(error?.message || error?.details?.message || 'Failed to create product. Please check the details and try again.');
    }
  };

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products', to: '/products' },
          { label: 'Add Product' },
        ]}
      />

      {errorMsg && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
          <span>{errorMsg}</span>
        </div>
      )}

      <ProductForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default ProductCreatePage;
