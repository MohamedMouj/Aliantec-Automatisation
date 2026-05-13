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
        
        temp_base = Path(__file__).resolve().parent / 'temp'
        temp_base.mkdir(exist_ok=True)
        
        request_temp = temp_base / str(uuid.uuid4())
        request_temp.mkdir(exist_ok=True)
        
        try:
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, 'wb+') as destination:
                for chunk in uploaded_excel.chunks():
                    destination.write(chunk)
            
            zip_path = request_temp / uploaded_zip.name
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_zip.chunks():
                    destination.write(chunk)
            
            extract_path = request_temp / 'extracted'
            extract_path.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            exctract_old_path = extract_path / "fscf" / 'OLD'
            exctract_new_path = extract_path / "fscf" / 'NEW'
            processor = CompareProcess(
                excel_file=str(excel_path),
                old_folder=str(exctract_old_path),
                new_folder=str(exctract_new_path)
            )
            results = processor.start()
            
        finally:
            if 'processor' in locals():
                processor.close()
            shutil.rmtree(request_temp, ignore_errors=True)

    return render(request, 'FSCFAI_Compare/main.html', {'results': results})