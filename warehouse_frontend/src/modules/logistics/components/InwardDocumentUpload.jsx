import React, { useRef, useState } from 'react';
import Button from '../../../components/ui/Button';
import { Upload, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { logisticsApi } from '../api/logistics.api';

const mergeParsed = (prev, next, fileName) => {
  if (!prev) {
    return { ...next, source_files: [fileName] };
  }
  const warnings = [...(prev.warnings || []), ...(next.warnings || [])];
  const prevRef = prev.reference_document_number || prev.invoice_number;
  const nextRef = next.reference_document_number || next.invoice_number;
  if (prevRef && nextRef && prevRef !== nextRef) {
    warnings.push(
      `${fileName}: document no. ${nextRef} — lines added; header kept from first PDF (${prevRef}).`
    );
  }
  if (prev.vendor_id && next.vendor_id && prev.vendor_id !== next.vendor_id) {
    warnings.push(`${fileName}: supplier does not match the first PDF.`);
  }
  const prevPack = Number(prev.packing_weight);
  const nextPack = Number(next.packing_weight);
  const packing_weight =
    Number.isFinite(prevPack) && prevPack > 0 && Number.isFinite(nextPack) && nextPack > 0
      ? prevPack + nextPack
      : prev.packing_weight ?? next.packing_weight;

  return {
    ...prev,
    items: [...(prev.items || []), ...(next.items || [])],
    packing_weight,
    warnings,
    source_files: [...(prev.source_files || []), fileName],
  };
};

const InwardDocumentUpload = ({ onParsed, render, multiple = false }) => {
  const inputRef = useRef(null);
  const [isParsing, setIsParsing] = useState(false);
  const [error, setError] = useState(null);
  const [lastParse, setLastParse] = useState(null);
  const [fileLabels, setFileLabels] = useState([]);
  const [showMapping, setShowMapping] = useState(false);

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || []).filter((f) => f);
    if (!files.length) return;
    setError(null);
    setIsParsing(true);
    let merged = lastParse;
    const labels = multiple ? [...fileLabels] : [];
    try {
      for (const file of files) {
        const data = await logisticsApi.inward.parseDocument(file);
        merged = mergeParsed(merged, data, file.name);
        labels.push(file.name);
      }
      setLastParse(merged);
      setFileLabels(labels);
      setShowMapping(false);
      onParsed?.(merged);
    } catch (err) {
      setError(err?.message || 'Failed to parse PDF');
      if (!multiple) {
        setLastParse(null);
        setFileLabels([]);
      }
    } finally {
      setIsParsing(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const clearUploads = () => {
    setLastParse(null);
    setFileLabels([]);
    setError(null);
    onParsed?.(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const trigger = (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        multiple={multiple}
        disabled={isParsing}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="flex flex-wrap items-center gap-2 justify-end">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          leftIcon={<Upload className="w-4 h-4" />}
          isLoading={isParsing}
          onClick={() => inputRef.current?.click()}
        >
          {isParsing ? 'Reading…' : multiple ? 'Upload PDF(s)' : 'Upload PDF'}
        </Button>
        {multiple && fileLabels.length > 0 && (
          <Button type="button" size="sm" variant="ghost" onClick={clearUploads}>
            Clear PDFs
          </Button>
        )}
      </div>
    </>
  );

  const hasFeedback = error || fileLabels.length || lastParse?.warnings?.length || lastParse?.field_status?.length;

  const feedback = hasFeedback ? (
    <div className="space-y-2">
      {fileLabels.length > 0 && !error && (
        <div className="text-xs text-gray-500 space-y-1">
          <p className="font-medium text-gray-700">
            {multiple ? `Loaded ${fileLabels.length} PDF(s):` : 'Loaded:'}
          </p>
          <ul className="list-disc list-inside max-h-24 overflow-y-auto">
            {fileLabels.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
          {multiple && lastParse?.items?.length > 0 && (
            <p className="text-gray-600">{lastParse.items.length} line(s) on the inward form.</p>
          )}
        </div>
      )}
      {error && (
        <p className="text-sm text-red-600 flex items-center gap-1">
          <AlertCircle className="w-4 h-4 shrink-0" /> {error}
        </p>
      )}
      {lastParse?.warnings?.length > 0 && (
        <ul className="text-sm text-amber-800 bg-amber-50 rounded-lg px-3 py-2 space-y-0.5">
          {lastParse.warnings.map((w) => (
            <li key={w}>• {w}</li>
          ))}
        </ul>
      )}
      {lastParse?.field_status?.length > 0 && (
        <div className="border border-gray-100 rounded-lg overflow-hidden">
          <button
            type="button"
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50 hover:bg-gray-100"
            onClick={() => setShowMapping((v) => !v)}
          >
            Invoice field mapping
            {showMapping ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showMapping && (
            <div className="overflow-x-auto max-h-48 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-white text-gray-500 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-1.5">Field</th>
                    <th className="text-left px-3 py-1.5">Extracted</th>
                    <th className="text-left px-3 py-1.5">WMS</th>
                    <th className="text-left px-3 py-1.5">OK</th>
                  </tr>
                </thead>
                <tbody>
                  {lastParse.field_status.map((row) => (
                    <tr key={row.invoice_field} className="border-t border-gray-50">
                      <td className="px-3 py-1.5 font-medium">{row.invoice_field}</td>
                      <td className="px-3 py-1.5 text-gray-600 max-w-[140px] truncate">
                        {row.extracted_value || '—'}
                      </td>
                      <td className="px-3 py-1.5 text-gray-500">{row.maps_to_wms || '—'}</td>
                      <td className="px-3 py-1.5">
                        {row.capturable ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                        ) : (
                          <span className="text-amber-700" title={row.note || ''}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  ) : null;

  if (render) {
    return render({ trigger, feedback });
  }

  return (
    <div className="flex flex-col items-end gap-2">
      {trigger}
      <div className="w-full">{feedback}</div>
    </div>
  );
};

export default InwardDocumentUpload;
