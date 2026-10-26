import React, { useState } from 'react';
import { Upload, Download, FileSpreadsheet, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';

const MigrationPage = () => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedModule, setSelectedModule] = useState('products');

  const migrationModules = [
    { id: 'products', name: 'Products & SKUs', description: 'Import master product list and SKU configurations' },
    { id: 'vendors', name: 'Suppliers', description: 'Bulk import supplier contact information' },
    { id: 'inventory', name: 'Initial Stock', description: 'Set starting inventory levels for all warehouses' },
    { id: 'locations', name: 'Warehouse Locations', description: 'Configure zones, aisles, and bins' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Migration & Import</h1>
          <p className="text-gray-500">Bulk import data using Excel or CSV templates</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider px-2">Select Module</h3>
          {migrationModules.map((mod) => (
            <button
              key={mod.id}
              onClick={() => setSelectedModule(mod.id)}
              className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                selectedModule === mod.id 
                  ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200 ring-offset-2' 
                  : 'border-gray-100 bg-white hover:border-gray-200'
              }`}
            >
              <h4 className={`font-bold ${selectedModule === mod.id ? 'text-primary-700' : 'text-gray-900'}`}>{mod.name}</h4>
              <p className="text-xs text-gray-500 mt-1">{mod.description}</p>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <Card.Header>
              <Card.Title>Import {migrationModules.find(m => m.id === selectedModule)?.name}</Card.Title>
            </Card.Header>
            <Card.Body className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-100 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="bg-blue-600 p-2 rounded-lg text-white">
                    <FileSpreadsheet size={20} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-blue-900">Template required?</p>
                    <p className="text-xs text-blue-700">Download the standard format to ensure data integrity.</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" leftIcon={<Download size={14} />}>Download Template</Button>
              </div>

              <div 
                className={`border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center transition-colors ${
                  dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(e) => { e.preventDefault(); setDragActive(false); }}
              >
                <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-4">
                  <Upload size={32} />
                </div>
                <h4 className="text-lg font-medium text-gray-900">Drop your file here or click to browse</h4>
                <p className="text-sm text-gray-500 mt-1">Supports .xlsx, .xls and .csv files (Max 10MB)</p>
                <input type="file" className="hidden" />
                <Button className="mt-6">Choose File</Button>
              </div>

              <div className="space-y-4">
                <h5 className="text-sm font-semibold text-gray-900">Recent Imports</h5>
                <div className="border border-gray-100 rounded-lg overflow-hidden">
                  {[1, 2].map((i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-white border-b border-gray-100 last:border-0">
                      <div className="flex items-center space-x-3">
                        {i === 1 ? <CheckCircle2 className="text-emerald-500" size={18} /> : <AlertCircle className="text-red-500" size={18} />}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{i === 1 ? 'product_list_sept.xlsx' : 'supplier_import_v2.csv'}</p>
                          <p className="text-xs text-gray-500">2026-09-18 • {i === 1 ? '1,240 records imported' : 'Failed at row 42'}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" rightIcon={<ArrowRight size={14} />}>View Details</Button>
                    </div>
                  ))}
                </div>
              </div>
            </Card.Body>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default MigrationPage;
