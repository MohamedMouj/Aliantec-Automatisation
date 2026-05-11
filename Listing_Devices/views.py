import os
import shutil
import zipfile
import io
import uuid
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse
from .helpers.process import DevicesProcess

def index(request):
    results = None
    if request.method == 'POST' and request.FILES.get('input_zip'):
        uploaded_zip = request.FILES['input_zip']
        
        temp_base = Path(__file__).resolve().parent / 'temp'
        temp_base.mkdir(exist_ok=True)
        session_id = uuid.uuid4().hex[:8]
        request_temp = temp_base / session_id
        if request_temp.exists():
            shutil.rmtree(request_temp, ignore_errors=True)
        request_temp.mkdir(exist_ok=True)
        
        try:
            zip_path = request_temp / uploaded_zip.name
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_zip.chunks():
                    destination.write(chunk)
            
            extract_path = request_temp / 'extracted'
            extract_path.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            
            excel_path = request_temp / 'all_devices.xlsx'
            
            processor = DevicesProcess(
                folder_path=str(extract_path),
                output_file=str(excel_path)
            )
            success = processor.start()
            
            if success and excel_path.exists():
                # Read file into memory so we can delete the folder before returning
                with open(excel_path, 'rb') as f:
                    file_data = io.BytesIO(f.read())
                
                return FileResponse(
                    file_data, 
                    as_attachment=True, 
                    filename='all_devices.xlsx'
                )
            else:
                return render(request, "Listing_Devices/main.html", {"error": "No device data could be extracted."})
                
        except Exception as e:
            return render(request, "Listing_Devices/main.html", {"error": str(e)})
            
        finally:
            if 'request_temp' in locals() and request_temp.exists():
                shutil.rmtree(request_temp, ignore_errors=True)
        
    return render(request, "Listing_Devices/main.html")
