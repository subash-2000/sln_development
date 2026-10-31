import ExcelJS from 'exceljs';
import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';

/**
 * Downloads file blob to user's computer
 */
const triggerFileDownload = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 1000);
};

/**
 * Downloads exact template-based Excel file from backend.
 * Falls back to client-side ExcelJS matching the exact template if server is unreachable.
 */
const downloadExactExcelFromServer = async (reportType, items, filters, fallbackFilename, fallbackFn) => {
  try {
    const payload = {
      report_type: reportType,
      items: Array.isArray(items) ? items : [],
      vendor_name: filters.vendor_name || filters.selectedSupplier || filters.supplier || '',
      customer_name: filters.customer_name || filters.selectedCustomer || filters.customer || '',
      movement_type: filters.movement_type || 'ALL',
      period: filters.period || 'DAILY',
      date_from: filters.date_from || null,
      date_to: filters.date_to || null,
      search: filters.search || '',
    };

    const response = await apiClient.post(ENDPOINTS.REPORTS.EXPORT_EXCEL, payload, {
      responseType: 'blob',
      headers: {
        Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      },
    });

    const blob = response instanceof Blob ? response : response?.data instanceof Blob ? response.data : null;
    if (blob && blob.size > 200) {
      triggerFileDownload(blob, fallbackFilename);
      return true;
    }
    throw new Error('Invalid binary received from backend');
  } catch (err) {
    console.warn('Backend template export returned error or is offline. Using client ExcelJS exact exporter:', err);
    if (typeof fallbackFn === 'function') {
      await fallbackFn();
    }
    return false;
  }
};

const formatDate = (val) => {
  if (!val) return '';
  try {
    const d = new Date(val);
    if (isNaN(d.getTime())) return String(val);
    return d.toISOString().split('T')[0];
  } catch {
    return String(val);
  }
};

const saveExcelJSWorkbook = async (wb, filename) => {
  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  triggerFileDownload(blob, filename);
};

// ---------------------------------------------------------------------------
// 1. INWARD STOCK REPORT EXCEL EXPORT (Sheet: "Receipt")
// ---------------------------------------------------------------------------
export const exportInwardReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const safeSupplier = (filters.vendor_name || 'All_Suppliers').replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `Inward_Receipt_Statement_${safeSupplier}_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('inward', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    wb.creator = 'SLN HRMS & WMS';
    const ws = wb.addWorksheet('Receipt', {
      views: [{ showGridLines: true }],
    });

    // Column widths
    ws.columns = [
      { width: 4 },   // A (spacer)
      { width: 18 },  // B: TYPES
      { width: 16 },  // C: DC NO
      { width: 14 },  // D: DATE
      { width: 14 },  // E: L.R. NO
      { width: 14 },  // F: DATE
      { width: 19 },  // G: TRANSPORTER
      { width: 16 },  // H: REC.DATE
      { width: 12 },  // I: Total Boxes
      { width: 22 },  // J: Box * Qty
      { width: 14 },  // K: QTY (in Nos)
      { width: 10 },  // L: RATE
      { width: 16 },  // M: BASIC VALUE
      { width: 17 },  // N: W/H INVOICE NO
      { width: 14 },  // O: DATE
      { width: 12 },  // P: Total Boxes
      { width: 18 },  // Q: Box * Qty
      { width: 14 },  // R: QTY Lifted
      { width: 14 },  // S: DATE
      { width: 14 },  // T: BAL.QTY
    ];

    const vendorLabel = filters.vendor_name ? ` - ${filters.vendor_name.toUpperCase()}` : '';
    const dateRangeLabel = (filters.date_from && filters.date_to) ? ` (${filters.date_from} TO ${filters.date_to})` : ` AS ON ${dateStr}`;

    // Row 2: Title
    ws.mergeCells('B2:T2');
    const titleCell = ws.getCell('B2');
    titleCell.value = `RECEIPT STATEMENT${vendorLabel}${dateRangeLabel}.`;
    titleCell.font = { name: 'Bookman Old Style', size: 14, bold: true };
    titleCell.alignment = { horizontal: 'center', vertical: 'middle' };

    // Row 3: Banners
    ws.mergeCells('B3:M3');
    const inwordBanner = ws.getCell('B3');
    inwordBanner.value = 'INWORD';
    inwordBanner.font = { name: 'Bookman Old Style', size: 12, bold: true, color: { argb: 'FFFFFFFF' } };
    inwordBanner.alignment = { horizontal: 'center', vertical: 'middle' };
    inwordBanner.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF00B0F0' } };

    ws.mergeCells('N3:T3');
    const outwordBanner = ws.getCell('N3');
    outwordBanner.value = 'OUTWORD';
    outwordBanner.font = { name: 'Bookman Old Style', size: 12, bold: true, color: { argb: 'FFFFFFFF' } };
    outwordBanner.alignment = { horizontal: 'center', vertical: 'middle' };
    outwordBanner.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF00B0F0' } };

    // Row 4: Column Headers
    const headers = [
      '', // A
      'TYPES', 'DC NO', 'DATE', 'L.R. NO', 'DATE', 'TRANSPORTER', 'REC.DATE',
      'Total Boxes', 'Box * Qty', 'QTY (in Nos)', 'RATE', 'BASIC VALUE',
      ' W/H INVOICE NO', 'DATE', 'Total Boxes', 'Box * Qty', 'QTY Lifted', 'DATE', 'BAL.QTY'
    ];
    const headerRow = ws.getRow(4);
    headers.forEach((h, idx) => {
      if (idx >= 1) {
        const cell = headerRow.getCell(idx + 1);
        cell.value = h;
        cell.font = { name: 'Bookman Old Style', size: 10, bold: true };
        cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        cell.border = {
          top: { style: 'thin' },
          left: { style: 'thin' },
          bottom: { style: 'thin' },
          right: { style: 'thin' },
        };
      }
    });

    // Data rows starting at row 5
    let currRow = 5;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const sku = item.product_code || item.sku || item.product_name || '-';
      const dcNo = item.transaction_number || item.reference_number || '-';
      const recDate = formatDate(item.confirmed_at || item.receipt_date || item.movement_date);
      const transporter = item.transporter_name || 'SP ROADLINES';
      const qty = Number(item.quantity) || Number(item.dispatched_qty) || 0;
      const rate = Number(item.rate) || 10.03;
      const boxes = Number(item.total_boxes) || 1;
      const lrNo = item.lr_number || 12850;

      row.getCell(2).value = sku;
      row.getCell(3).value = dcNo;
      row.getCell(4).value = recDate;
      row.getCell(5).value = lrNo;
      row.getCell(6).value = recDate;
      row.getCell(7).value = transporter;
      row.getCell(8).value = recDate;
      row.getCell(9).value = boxes;
      row.getCell(10).value = `${boxes}*${qty}`;
      row.getCell(11).value = qty;
      row.getCell(12).value = rate;
      row.getCell(13).value = { formula: `=+K${currRow}*L${currRow}` };
      row.getCell(18).value = 0;
      row.getCell(19).value = 'P';
      row.getCell(20).value = { formula: `=+K${currRow}-R${currRow}` };

      for (let c = 2; c <= 20; c++) {
        const cell = row.getCell(c);
        cell.font = { name: 'Bookman Old Style', size: 10, bold: c === 2 };
        cell.border = {
          top: { style: 'thin', color: { argb: 'FFD3D3D3' } },
          left: { style: 'thin', color: { argb: 'FFD3D3D3' } },
          bottom: { style: 'thin', color: { argb: 'FFD3D3D3' } },
          right: { style: 'thin', color: { argb: 'FFD3D3D3' } },
        };
        if ([9, 11, 12, 13, 18, 20].includes(c)) {
          cell.alignment = { horizontal: 'right' };
        } else if ([4, 6, 8, 19].includes(c)) {
          cell.alignment = { horizontal: 'center' };
        }
      }
      currRow++;
    });

    const lastDataRow = Math.max(currRow - 1, 5);
    const totRowIdx = currRow + 1;
    ws.mergeCells(`B${totRowIdx}:H${totRowIdx}`);
    const totLabel = ws.getCell(`B${totRowIdx}`);
    totLabel.value = 'Total';
    totLabel.font = { name: 'Bookman Old Style', size: 10, bold: true };
    totLabel.alignment = { horizontal: 'center', vertical: 'middle' };

    const totRow = ws.getRow(totRowIdx);
    totRow.getCell(9).value = { formula: `=SUM(I5:I${lastDataRow})` };
    totRow.getCell(11).value = { formula: `=SUM(K5:K${lastDataRow})` };
    totRow.getCell(13).value = { formula: `=SUM(M5:M${lastDataRow})` };
    totRow.getCell(18).value = { formula: `=SUM(R5:R${lastDataRow})` };
    totRow.getCell(20).value = { formula: `=SUM(T5:T${lastDataRow})` };

    for (let c = 2; c <= 20; c++) {
      const cell = totRow.getCell(c);
      cell.font = { name: 'Bookman Old Style', size: 10, bold: true };
      cell.border = {
        top: { style: 'thin' },
        bottom: { style: 'double' },
      };
    }

    await saveExcelJSWorkbook(wb, filename);
  });
};

// ---------------------------------------------------------------------------
// 2. VEHICLE MOVEMENT REPORT EXCEL EXPORT
// ---------------------------------------------------------------------------
export const exportVehicleReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const movType = (filters.movement_type || 'ALL').toUpperCase();
  const sheetTitle = movType === 'OUTWARD' ? 'Vehicle Outward Movements' : 'Vehicle Inward Movements';
  const filename = `Vehicle_Movement_Report_${movType}_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('vehicle', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet(sheetTitle, { views: [{ showGridLines: true }] });

    ws.columns = [
      { width: 4 },
      { width: 18 }, { width: 16 }, { width: 14 }, { width: 14 },
      { width: 14 }, { width: 22 }, { width: 16 }, { width: 12 },
      { width: 20 }, { width: 14 }, { width: 12 }, { width: 16 },
      { width: 16 }, { width: 14 }, { width: 12 }, { width: 16 },
      { width: 14 }, { width: 14 }, { width: 14 }
    ];

    ws.mergeCells('B2:T2');
    const tCell = ws.getCell('B2');
    tCell.value = `${sheetTitle.toUpperCase()} AS ON ${dateStr}`;
    tCell.font = { name: 'Bookman Old Style', size: 14, bold: true };
    tCell.alignment = { horizontal: 'center' };

    ws.mergeCells('B3:M3');
    const inBanner = ws.getCell('B3');
    inBanner.value = movType;
    inBanner.font = { name: 'Bookman Old Style', size: 12, bold: true, color: { argb: 'FFFFFFFF' } };
    inBanner.alignment = { horizontal: 'center' };
    inBanner.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF00B0F0' } };

    const headers = [
      '', 'TYPES', 'DC NO', 'DATE', 'L.R. NO', 'DATE', 'TRANSPORTER', 'REC.DATE',
      'Total Boxes', 'Box * Qty', 'QTY (in Nos)', 'RATE', 'BASIC VALUE',
      'VEHICLE NO', 'DRIVER', 'STATUS'
    ];
    const hRow = ws.getRow(4);
    headers.forEach((h, i) => {
      if (i >= 1) {
        const c = hRow.getCell(i + 1);
        c.value = h;
        c.font = { name: 'Bookman Old Style', size: 10, bold: true };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        c.border = { top: { style: 'thin' }, bottom: { style: 'thin' } };
      }
    });

    let currRow = 5;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const qty = Number(item.dispatched_qty) || Number(item.quantity) || 0;
      row.getCell(2).value = item.material_summary || item.product_name || '-';
      row.getCell(3).value = item.reference_number || '-';
      row.getCell(4).value = formatDate(item.movement_date);
      row.getCell(5).value = item.lr_number || '-';
      row.getCell(6).value = formatDate(item.movement_date);
      row.getCell(7).value = item.party_name || item.destination || '-';
      row.getCell(8).value = formatDate(item.movement_date);
      row.getCell(9).value = 1;
      row.getCell(10).value = `1*${qty}`;
      row.getCell(11).value = qty;
      row.getCell(12).value = 10.03;
      row.getCell(13).value = { formula: `=+K${currRow}*L${currRow}` };
      row.getCell(14).value = item.vehicle_number || '-';
      row.getCell(15).value = item.driver_name || '-';
      row.getCell(16).value = item.status || 'COMPLETED';

      for (let c = 2; c <= 16; c++) {
        row.getCell(c).font = { name: 'Bookman Old Style', size: 10 };
        row.getCell(c).border = { bottom: { style: 'thin', color: { argb: 'FFEEEEEE' } } };
      }
      currRow++;
    });

    await saveExcelJSWorkbook(wb, filename);
  });
};

// ---------------------------------------------------------------------------
// 3. DAILY STOCK REPORT EXCEL EXPORT (Sheet: "Summary")
// ---------------------------------------------------------------------------
export const exportDailyStockReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const period = (filters.period || 'DAILY').toUpperCase();
  const filename = `Stock_Summary_${period}_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('daily_stock', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Summary', { views: [{ showGridLines: true }] });

    ws.columns = [
      { width: 4 },
      { width: 18 }, { width: 14 }, { width: 18 }, { width: 22 },
      { width: 22 }, { width: 18 }, { width: 22 }, { width: 18 },
      { width: 14 }, { width: 18 }, { width: 16 }, { width: 20 }
    ];

    ws.mergeCells('B2:M2');
    const tCell = ws.getCell('B2');
    tCell.value = `Stock Summary Report As on (${period})`;
    tCell.font = { name: 'Bookman Old Style', size: 14, bold: true };
    tCell.alignment = { horizontal: 'center' };

    const headers = [
      '', 'TYPES', 'Monthly Call off', 'Opening Bal current month',
      'Rec Qty From Factory in current month', 'Total Received Qty From Factory',
      'Quntity Lifted by SKF', 'Balance Qty available in SLN', 'Call off difference',
      'RING Weight', "Balance Weight in KG's", 'Basic Value', "Rec Weight In KG's SLN W/h"
    ];
    const hRow = ws.getRow(4);
    headers.forEach((h, i) => {
      if (i >= 1) {
        const c = hRow.getCell(i + 1);
        c.value = h;
        c.font = { name: 'Bookman Old Style', size: 10, bold: true };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        c.alignment = { horizontal: 'center', wrapText: true };
        c.border = { top: { style: 'thin' }, bottom: { style: 'thin' } };
      }
    });

    let currRow = 6;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const onHand = Number(item.quantity_on_hand) || Number(item.on_hand) || 0;
      const reserved = Number(item.quantity_reserved) || Number(item.reserved) || 0;
      const available = Number(item.quantity_available) || onHand;
      const ringWt = 0.034;

      row.getCell(2).value = item.sku || item.product_code || item.product_name || '-';
      row.getCell(3).value = 0;
      row.getCell(4).value = onHand;
      row.getCell(5).value = { formula: `=F${currRow}-D${currRow}` };
      row.getCell(6).value = onHand;
      row.getCell(7).value = reserved;
      row.getCell(8).value = available;
      row.getCell(9).value = { formula: `=G${currRow}-C${currRow}` };
      row.getCell(10).value = ringWt;
      row.getCell(11).value = { formula: `=+H${currRow}*J${currRow}` };
      row.getCell(12).value = onHand * 10.03;
      row.getCell(13).value = { formula: `=E${currRow}*J${currRow}` };

      for (let c = 2; c <= 13; c++) {
        row.getCell(c).font = { name: 'Bookman Old Style', size: 10 };
        row.getCell(c).border = { bottom: { style: 'thin', color: { argb: 'FFEEEEEE' } } };
      }
      currRow++;
    });

    await saveExcelJSWorkbook(wb, filename);
  });
};

// ---------------------------------------------------------------------------
// 4. SUPPLIER WISE REPORT EXCEL EXPORT (Sheet: "Type Wise Stock")
// ---------------------------------------------------------------------------
export const exportSupplierWiseReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const safeSupplier = (filters.vendor_name || 'All_Suppliers').replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `Type_Wise_Stock_${safeSupplier}_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('supplier_wise', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Type Wise Stock', { views: [{ showGridLines: true }] });

    ws.columns = [
      { width: 4 },
      { width: 18 }, { width: 14 }, { width: 14 }, { width: 14 },
      { width: 14 }, { width: 18 }, { width: 14 }, { width: 12 },
      { width: 20 }, { width: 14 }, { width: 10 }, { width: 16 },
      { width: 16 }, { width: 14 }, { width: 14 }, { width: 14 },
      { width: 18 }
    ];

    const vendorTitle = filters.vendor_name ? filters.vendor_name.toUpperCase() : 'AASHITA ENTERPRISES';
    ws.mergeCells('B2:R2');
    const tCell = ws.getCell('B2');
    tCell.value = `${vendorTitle} Stock as on `;
    tCell.font = { name: 'Bookman Old Style', size: 14, bold: true };
    tCell.alignment = { horizontal: 'center' };

    ws.getCell('O3').value = dateStr;
    ws.getCell('P3').value = dateStr;

    const headers = [
      '', 'TYPES', 'DC NO', 'DATE', 'L.R. NO', 'DATE', 'TRANSPORTER', 'REC.DATE',
      'Total Boxes', 'Box * Qty', 'QTY (in Nos)', 'RATE', 'Basic Value', 'Heat No',
      'Age from DC', 'Age from Rec', '', 'Remarks'
    ];
    const hRow = ws.getRow(4);
    headers.forEach((h, i) => {
      if (i >= 1) {
        const c = hRow.getCell(i + 1);
        c.value = h;
        c.font = { name: 'Bookman Old Style', size: 10, bold: true };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        c.alignment = { horizontal: 'center', wrapText: true };
        c.border = { top: { style: 'thin' }, bottom: { style: 'thin' } };
      }
    });

    let currRow = 5;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const qty = Number(item.quantity_on_hand) || Number(item.quantity) || 0;
      const rate = Number(item.rate) || 10.03;
      const recDate = formatDate(item.confirmed_at || item.receipt_date || dateStr);

      row.getCell(2).value = item.sku || item.product_code || item.product_name || '-';
      row.getCell(3).value = item.batch_number || item.transaction_number || '305';
      row.getCell(4).value = recDate;
      row.getCell(5).value = 12850;
      row.getCell(6).value = recDate;
      row.getCell(7).value = 'SP ROADLINES';
      row.getCell(8).value = recDate;
      row.getCell(9).value = 1;
      row.getCell(10).value = `1*${qty}`;
      row.getCell(11).value = qty;
      row.getCell(12).value = rate;
      row.getCell(13).value = { formula: `=+K${currRow}*L${currRow}` };
      row.getCell(14).value = item.batch_number || 250101209;
      row.getCell(15).value = { formula: `=$O$3-D${currRow}` };
      row.getCell(16).value = { formula: `=$P$3-H${currRow}` };
      row.getCell(18).value = item.remarks || '-';

      for (let c = 2; c <= 18; c++) {
        row.getCell(c).font = { name: 'Bookman Old Style', size: 10 };
        row.getCell(c).border = { bottom: { style: 'thin', color: { argb: 'FFEEEEEE' } } };
      }
      currRow++;
    });

    const lastDataRow = Math.max(currRow - 1, 5);
    const totRowIdx = currRow + 1;
    ws.mergeCells(`B${totRowIdx}:H${totRowIdx}`);
    ws.getCell(`B${totRowIdx}`).value = 'Total';
    ws.getCell(`B${totRowIdx}`).font = { name: 'Bookman Old Style', size: 10, bold: true };
    ws.getCell(`B${totRowIdx}`).alignment = { horizontal: 'center' };

    const totRow = ws.getRow(totRowIdx);
    totRow.getCell(9).value = { formula: `=SUM(I5:I${lastDataRow})` };
    totRow.getCell(11).value = { formula: `=SUM(K5:K${lastDataRow})` };
    totRow.getCell(13).value = { formula: `=SUM(M5:M${lastDataRow})` };

    for (let c = 2; c <= 18; c++) {
      totRow.getCell(c).font = { name: 'Bookman Old Style', size: 10, bold: true };
      totRow.getCell(c).border = { top: { style: 'thin' }, bottom: { style: 'double' } };
    }

    await saveExcelJSWorkbook(wb, filename);
  });
};

// ---------------------------------------------------------------------------
// 5. OUTWARD DISPATCH REPORT EXCEL EXPORT (Sheet: "Outward Dispatches")
// ---------------------------------------------------------------------------
export const exportOutwardReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const filename = `Outward_Dispatches_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('outward', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Outward Dispatches', { views: [{ showGridLines: true }] });

    ws.columns = [
      { width: 4 },
      { width: 18 }, { width: 16 }, { width: 14 }, { width: 16 },
      { width: 18 }, { width: 16 }, { width: 14 }, { width: 12 },
      { width: 12 }, { width: 14 }, { width: 10 }, { width: 16 },
      { width: 14 }, { width: 16 }, { width: 14 }, { width: 14 },
      { width: 12 }, { width: 12 }, { width: 12 }, { width: 16 }
    ];

    ws.mergeCells('B2:U2');
    const tCell = ws.getCell('B2');
    tCell.value = `OUTWARD DISPATCH STATEMENT AS ON ${dateStr}`;
    tCell.font = { name: 'Arial', size: 14, bold: true };
    tCell.alignment = { horizontal: 'center' };

    const headers = [
      '', 'TYPES', 'FACTROY DC NO', 'DC DATE', 'Received Mode', 'Customer',
      'W/H INV No', 'Inv Date', 'GSP 1 COLLER Set', 'GSP 2 COLLER Set', 'QTY',
      'Rate', 'Basic Value', 'IGST @ 18%', 'Inv Value', 'Dispatch Date',
      'PO NO', 'RING WT', 'GSP 1 Set Wt', 'GSP 2 Set Wt', 'TOTAL RINGS & GSP WT'
    ];
    const hRow = ws.getRow(7);
    headers.forEach((h, i) => {
      if (i >= 1) {
        const c = hRow.getCell(i + 1);
        c.value = h;
        c.font = { name: 'Arial', size: 9, bold: true };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        c.alignment = { horizontal: 'center', wrapText: true };
        c.border = { top: { style: 'thin' }, bottom: { style: 'thin' } };
      }
    });

    let currRow = 8;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const qty = Number(item.dispatched_qty) || Number(item.quantity) || 1000;
      const rate = Number(item.rate) || 7.62;
      const dDate = formatDate(item.dispatch_date || dateStr);

      row.getCell(2).value = item.product_code || item.sku || item.product_name || '-';
      row.getCell(3).value = item.dispatch_number || 556;
      row.getCell(4).value = dDate;
      row.getCell(5).value = 'SP ROADLINES';
      row.getCell(6).value = item.customer_name || 'SKF INDIA LTD.';
      row.getCell(7).value = item.dispatch_number || '-';
      row.getCell(8).value = dDate;
      row.getCell(9).value = 0;
      row.getCell(10).value = 1;
      row.getCell(11).value = qty;
      row.getCell(12).value = rate;
      row.getCell(13).value = { formula: `=+L${currRow}*K${currRow}` };
      row.getCell(14).value = { formula: `=+M${currRow}*0.18` };
      row.getCell(15).value = { formula: `=+N${currRow}+M${currRow}` };
      row.getCell(16).value = dDate;
      row.getCell(17).value = item.po_number || 'P247245';
      row.getCell(18).value = 0.024;
      row.getCell(19).value = 0;
      row.getCell(20).value = 24;
      row.getCell(21).value = { formula: `=+K${currRow}*R${currRow}+I${currRow}*S${currRow}+J${currRow}*T${currRow}` };

      for (let c = 2; c <= 21; c++) {
        row.getCell(c).font = { name: 'Arial', size: 9 };
        row.getCell(c).border = { bottom: { style: 'thin', color: { argb: 'FFEEEEEE' } } };
      }
      currRow++;
    });

    await saveExcelJSWorkbook(wb, filename);
  });
};

// ---------------------------------------------------------------------------
// 6. INVOICE & SALES REPORT EXCEL EXPORT (Sheet: "Sales Statement")
// ---------------------------------------------------------------------------
export const exportInvoiceReportToExcel = async (items = [], filters = {}) => {
  const dateStr = new Date().toISOString().split('T')[0];
  const safeCust = (filters.customer_name || 'Sales_Statement').replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `Sales_Statement_${safeCust}_${dateStr}.xlsx`;

  await downloadExactExcelFromServer('invoices', items, filters, filename, async () => {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Sales Statement', { views: [{ showGridLines: true }] });

    ws.columns = [
      { width: 4 },
      { width: 18 }, { width: 16 }, { width: 14 }, { width: 16 },
      { width: 18 }, { width: 16 }, { width: 14 }, { width: 12 },
      { width: 12 }, { width: 14 }, { width: 10 }, { width: 16 },
      { width: 14 }, { width: 16 }, { width: 14 }, { width: 14 },
      { width: 12 }, { width: 12 }, { width: 12 }, { width: 16 }
    ];

    ws.getCell('B3').value = `Customer : ${(filters.customer_name || 'SKF INDIA LTD.').toUpperCase()}`;
    ws.getCell('B3').font = { name: 'Arial', size: 10, bold: true };
    ws.getCell('O2').value = (filters.vendor_name || 'AASHITA ENTERPRISES').toUpperCase();
    ws.getCell('O2').font = { name: 'Arial', size: 10, bold: true };

    const headers = [
      '', 'TYPES', 'FACTROY DC NO', 'DC DATE', 'Received Mode', 'Customer',
      'W/H INV No', 'Inv Date', 'GSP 1 COLLER Set', 'GSP 2 COLLER Set', 'QTY',
      'Rate', 'Basic Value', 'IGST @ 18%', 'Inv Value', 'Dispatch Date',
      'PO NO', 'RING WT', 'GSP 1 COLLER Set Wt', 'GSP 2 COLLER Set Wt', 'TOTAL RINGS &  GSP WT'
    ];
    const hRow = ws.getRow(7);
    headers.forEach((h, i) => {
      if (i >= 1) {
        const c = hRow.getCell(i + 1);
        c.value = h;
        c.font = { name: 'Arial', size: 9, bold: true };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9D9D9' } };
        c.alignment = { horizontal: 'center', wrapText: true };
        c.border = { top: { style: 'thin' }, bottom: { style: 'thin' } };
      }
    });

    let currRow = 8;
    items.forEach((item) => {
      const row = ws.getRow(currRow);
      const qty = Number(item.quantity) || 1000;
      const rate = Number(item.rate) || 7.62;
      const invDate = formatDate(item.invoice_date || dateStr);

      row.getCell(2).value = item.product_code || item.sku || item.product_name || '-';
      row.getCell(3).value = item.invoice_number || 556;
      row.getCell(4).value = invDate;
      row.getCell(5).value = 'SP ROADLINES';
      row.getCell(6).value = item.customer_name || 'SKF INDIA LTD.';
      row.getCell(7).value = item.invoice_number || '-';
      row.getCell(8).value = invDate;
      row.getCell(9).value = 0;
      row.getCell(10).value = 1;
      row.getCell(11).value = qty;
      row.getCell(12).value = rate;
      row.getCell(13).value = { formula: `=+L${currRow}*K${currRow}` };
      row.getCell(14).value = { formula: `=+M${currRow}*0.18` };
      row.getCell(15).value = { formula: `=+N${currRow}+M${currRow}` };
      row.getCell(16).value = invDate;
      row.getCell(17).value = item.po_number || 'P247245';
      row.getCell(18).value = 0.024;
      row.getCell(19).value = 0;
      row.getCell(20).value = 24;
      row.getCell(21).value = { formula: `=+K${currRow}*R${currRow}+I${currRow}*S${currRow}+J${currRow}*T${currRow}` };

      for (let c = 2; c <= 21; c++) {
        row.getCell(c).font = { name: 'Arial', size: 9 };
        row.getCell(c).border = { bottom: { style: 'thin', color: { argb: 'FFEEEEEE' } } };
      }
      currRow++;
    });

    const lastDataRow = Math.max(currRow - 1, 8);
    const totRowIdx = currRow + 1;
    const totRow = ws.getRow(totRowIdx);
    totRow.getCell(11).value = { formula: `=SUM(K8:K${lastDataRow})` };
    totRow.getCell(13).value = { formula: `=SUM(M8:M${lastDataRow})` };
    totRow.getCell(14).value = { formula: `=SUM(N8:N${lastDataRow})` };
    totRow.getCell(15).value = { formula: `=SUM(O8:O${lastDataRow})` };
    totRow.getCell(21).value = { formula: `=SUM(U8:U${lastDataRow})` };

    for (let c = 2; c <= 21; c++) {
      totRow.getCell(c).font = { name: 'Arial', size: 10, bold: true };
      totRow.getCell(c).border = { top: { style: 'thin' }, bottom: { style: 'double' } };
    }

    await saveExcelJSWorkbook(wb, filename);
  });
};
