import React, { useState } from 'react';

import { ChevronDown, Download, Upload } from 'lucide-react';

import Button from '../../../components/ui/Button';

import { inventoryApi } from '../api/inventory.api';



const OPTIONS = [

  { value: 'ALL', label: 'All suppliers (ZIP)' },

  { value: 'AASHITA', label: 'Aashita (Suppler 1 format)' },

  { value: 'MANU', label: 'Manu (Suppler 2 format)' },

  { value: 'NHB', label: 'NHB (Suppler 3 format)' },

];



const InventoryMasterExportMenu = ({ vendorId, vendors = [], onImported }) => {

  const [loading, setLoading] = useState(false);

  const [importing, setImporting] = useState(false);

  const [open, setOpen] = useState(false);



  const vendor = vendors.find((v) => v.id === vendorId);

  const vendorCode = vendor?.code?.toUpperCase();

  const filteredSupplier =

    vendorCode && ['AASHITA', 'MANU', 'NHB'].includes(vendorCode) ? vendorCode : null;



  const runExport = async (supplier) => {

    setLoading(true);

    setOpen(false);

    try {

      await inventoryApi.exportInventoryMaster(supplier);

    } catch (err) {
      console.error(err);
      window.alert(err?.message || 'Export failed. Please try again.');
    } finally {

      setLoading(false);

    }

  };



  const runImport = async () => {

    setOpen(false);

    const ok = window.confirm(

      'Import current stock from server sample Excel files (Suppler 1–3)?\n\n' +

        'This updates Current Stock, posts inward GRNs for increases, adjustments for decreases, ' +

        'and refreshes draft vendor return lines (Jaipur / rejected).'

    );

    if (!ok) return;

    setImporting(true);

    try {

      const summary = await inventoryApi.importInventoryMaster(false);

      const parts = [

        summary?.receipt_inward_grns

          ? `${summary.receipt_inward_grns} receipt inward(s)`

          : null,

        summary?.inward_grns ? `${summary.inward_grns} balance sync inward(s)` : null,

        summary?.adjustments ? `${summary.adjustments} adjustment(s)` : null,

        summary?.return_orders ? `${summary.return_orders} return register(s)` : null,

      ].filter(Boolean);

      window.alert(

        parts.length

          ? `Import complete: ${parts.join(', ')}.`

          : 'Import complete. Stock already matched the Excel balances.'

      );

      onImported?.();

    } catch (err) {

      console.error(err);

      window.alert(err?.message || 'Import failed. Check that sample Excel files exist on the server.');

    } finally {

      setImporting(false);

    }

  };



  return (

    <div className="relative">

      <Button

        variant="secondary"

        size="sm"

        leftIcon={<Download size={16} />}

        onClick={() => setOpen((v) => !v)}

        disabled={loading || importing}

        className="h-9 pr-2 shrink-0 whitespace-nowrap"

      >

        <span className="flex items-center gap-1 text-xs sm:text-sm">

          {loading ? 'Exporting…' : importing ? 'Importing…' : 'Inventory master'}

          <ChevronDown size={14} className="opacity-70 shrink-0" />

        </span>

      </Button>

      {open && !loading && !importing && (

        <>

          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden />

          <div className="absolute right-0 top-full mt-1 z-20 min-w-[15rem] rounded-lg border border-gray-200 bg-white shadow-lg py-1 text-sm">

            <button

              type="button"

              className="w-full text-left px-3 py-2 hover:bg-emerald-50 text-emerald-800 font-medium border-b border-gray-100 flex items-center gap-2"

              onClick={runImport}

            >

              <Upload size={14} />

              Import from sample Excel

            </button>

            {filteredSupplier && (

              <button

                type="button"

                className="w-full text-left px-3 py-2 hover:bg-primary-50 text-primary-700 font-medium border-b border-gray-100"

                onClick={() => runExport(filteredSupplier)}

              >

                {vendor?.name || filteredSupplier} (filtered)

              </button>

            )}

            {OPTIONS.map((opt) => (

              <button

                key={opt.value}

                type="button"

                className="w-full text-left px-3 py-2 hover:bg-gray-50 text-gray-800"

                onClick={() => runExport(opt.value)}

              >

                {opt.label}

              </button>

            ))}

          </div>

        </>

      )}

    </div>

  );

};



export default InventoryMasterExportMenu;


