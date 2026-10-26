import React, { useState, useRef } from 'react';
import { X, Upload, Check, AlertCircle, ChevronRight, FileText, Download } from 'lucide-react';
import Button from '../ui/Button';
import Card from '../ui/Card';
import { twMerge } from 'tailwind-merge';
import { migrationApi } from '../../services/api/migration.api';

/**
 * Enterprise Import Modal - Odoo Style
 * Logic: Upload -> Map Columns -> Validate -> Import
 */
const ImportModal = ({ 
  isOpen, 
  onClose, 
  title, 
  onImport, 
  fields = [], // { key: 'name', label: 'Name', required: true }
  sampleUrl,
  isLoading 
}) => {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [mapping, setMapping] = useState({});
  const [preview, setPreview] = useState([]);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      // In a real app, we would parse the headers here using a library like Papaparse or similar
      // For now, let's simulate step transition
      setStep(2);
      const dummyHeaders = fields.map((field) => field.label);
      const initialMapping = {};
      dummyHeaders.forEach((header) => {
        const field = fields.find(
          (item) => item.label.toLowerCase() === header.toLowerCase() || item.key.toLowerCase() === header.toLowerCase()
        );
        if (field) {
          initialMapping[header] = field.key;
        }
      });
      setMapping(initialMapping);
      setPreview(dummyHeaders);
    }
  };

  const handleImport = () => {
    if (onImport) {
      onImport({ file, mapping });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-primary-50 p-2 rounded-lg text-primary-600">
              <Upload size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Import {title}</h2>
              <p className="text-sm text-gray-500">Bulk upload your data via CSV or Excel</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* Stepper */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-100 flex items-center gap-4">
          <StepItem number={1} label="Upload" active={step === 1} completed={step > 1} />
          <ChevronRight className="text-gray-300" size={16} />
          <StepItem number={2} label="Map Columns" active={step === 2} completed={step > 2} />
          <ChevronRight className="text-gray-300" size={16} />
          <StepItem number={3} label="Preview & Import" active={step === 3} completed={step > 3} />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 1 && (
            <div className="space-y-6">
              <div 
                className={twMerge(
                  "border-2 border-dashed border-gray-200 rounded-xl p-12 flex flex-col items-center justify-center gap-4 transition-all cursor-pointer hover:border-primary-300 hover:bg-primary-50/30",
                  file && "border-primary-500 bg-primary-50/50"
                )}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="bg-white p-4 rounded-full shadow-sm text-primary-600 border border-gray-100">
                  <Upload size={32} />
                </div>
                <div className="text-center">
                  <p className="text-lg font-medium text-gray-900">Click to upload or drag and drop</p>
                  <p className="text-sm text-gray-500 mt-1">Excel (.xlsx) or CSV files supported</p>
                </div>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".csv, .xlsx, .xls"
                  onChange={handleFileChange} 
                />
              </div>

              <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg text-blue-700">
                <div className="flex items-center gap-3">
                  <FileText size={20} />
                  <span className="text-sm font-medium">Download template file for easier mapping</span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<Download size={16} />}
                  onClick={() => {
                    if (sampleUrl && /^[A-Z_]+$/.test(sampleUrl)) {
                      migrationApi.downloadTemplate(sampleUrl);
                      return;
                    }
                    if (sampleUrl) window.open(sampleUrl);
                  }}
                >
                  Template
                </Button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div className="overflow-hidden border border-gray-200 rounded-lg">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">File Column</th>
                      <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">System Field</th>
                      <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {preview.map(header => (
                      <tr key={header}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{header}</td>
                        <td className="px-4 py-3">
                          <select 
                            value={mapping[header] || ''}
                            onChange={(e) => setMapping({...mapping, [header]: e.target.value})}
                            className="w-full bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="">Don't Import</option>
                            {fields.map(field => (
                              <option key={field.key} value={field.key}>
                                {field.label} {field.required ? '*' : ''}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          {mapping[header] ? (
                            <span className="inline-flex items-center gap-1.5 text-green-600 text-xs font-medium">
                              <Check size={14} /> Mapped
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-gray-400 text-xs font-medium">
                              <AlertCircle size={14} /> Ignored
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <div className="flex gap-3">
            {step > 1 && (
              <Button variant="secondary" onClick={() => setStep(step - 1)} disabled={isLoading}>
                Back
              </Button>
            )}
            {step === 1 ? (
              <Button 
                variant="primary" 
                disabled={!file} 
                onClick={() => setStep(2)}
              >
                Continue
              </Button>
            ) : (
              <Button 
                variant="primary" 
                isLoading={isLoading} 
                onClick={handleImport}
              >
                Import Now
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const StepItem = ({ number, label, active, completed }) => (
  <div className={twMerge(
    "flex items-center gap-2 text-sm font-medium",
    active ? "text-primary-600" : completed ? "text-green-600" : "text-gray-400"
  )}>
    <div className={twMerge(
      "w-6 h-6 rounded-full flex items-center justify-center text-xs border transition-all",
      active ? "bg-primary-600 text-white border-primary-600 shadow-lg shadow-primary-100" : 
      completed ? "bg-green-100 text-green-600 border-green-200" : 
      "bg-white text-gray-400 border-gray-200"
    )}>
      {completed ? <Check size={14} /> : number}
    </div>
    <span>{label}</span>
  </div>
);

export default ImportModal;
