import os
import shutil
import zipfile
import uuid
from pathlib import Path
from django.shortcuts import render
from django.conf import settings
from .helpers.process import CompareProcess

def index(request):
    results = None
    if request.method == 'POST' and request.FILES.get('input_zip') and request.FILES.get('input_excel'):
        uploaded_zip = request.FILES['input_zip']
        uploaded_excel = request.FILES['input_excel']
        
        # Define application-specific temp directory
        app_dir = Path(__file__).resolve().parent
        temp_base = app_dir / 'temp'
        temp_base.mkdir(exist_ok=True)
        
        # Use a subfolder for this specific request to avoid collisions
        request_id = str(uuid.uuid4())
        request_temp = temp_base / request_id
        request_temp.mkdir(exist_ok=True)
        
        try:
            # Save Excel file
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, 'wb+') as destination:
                for chunk in uploaded_excel.chunks():
                    destination.write(chunk)
            
            # Save and Extract Zip file
            zip_path = request_temp / uploaded_zip.name
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_zip.chunks():
                    destination.write(chunk)
            
            extract_path = request_temp / 'extracted'
            extract_path.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # Run comparison
            processor = CompareProcess(
                excel_file=str(excel_path),
                folder_path=str(extract_path)
            )
            results = processor.start()
            
        finally:
            # Cleanup temp files after processing
            # shutil.rmtree(request_temp)
            pass

    return render(request, 'FSCFAI_Compare/main.html', {'results': results})