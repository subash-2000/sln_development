import io
import pandas as pd
from typing import List, Any, Dict
from fastapi.responses import StreamingResponse
from datetime import datetime

class ExportService:
    @staticmethod
    def to_csv(data: List[Dict[str, Any]], filename: str = "export"):
        df = pd.DataFrame(data)
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return response

    @staticmethod
    def to_excel(data: List[Dict[str, Any]], filename: str = "export"):
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        output.seek(0)
        response = StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return response
