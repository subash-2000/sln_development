import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useProduct, useUpdateProduct } from '../hooks/use-products';
import ProductForm from '../components/ProductForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const ProductEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: product, isLoading: isFetching } = useProduct(id);
  const { mutateAsync: updateProduct, isPending: isUpdating } = useUpdateProduct();
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSubmit = async (data) => {
    setErrorMsg(null);
    try {
      await updateProduct({
        id,
        data: {
          ...data,
          category_id: data.category_id ? data.category_id : null,
          secondary_uom_id: data.secondary_uom_id ? data.secondary_uom_id : null,
          hsn_code: data.hsn_code ? data.hsn_code.trim() : null,
          part_number: data.part_number?.trim() || null,
          description: data.description ? data.description.trim() : null,
          barcode: data.barcode ? data.barcode.trim() : null,
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
        },
      });
      navigate('/products');
    } catch (error) {
      console.error('Failed to update product:', error);
      setErrorMsg(error?.message || error?.details?.message || 'Failed to update product. Please check the details and try again.');
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Product"
        description="Update SKU details, descriptions and tracking configurations."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products', to: '/products' },
          { label: 'Edit Product' },
        ]}
      />

      {errorMsg && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
          <span>{errorMsg}</span>
        </div>
      )}

      <ProductForm 
        initialData={product} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default ProductEditPage;
