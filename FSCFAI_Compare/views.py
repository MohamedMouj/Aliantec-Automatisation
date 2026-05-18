import os
import shutil
import zipfile
import uuid
from pathlib import Path
from django.shortcuts import render
from django.conf import settings
from .helpers.process import CompareProcess
import base64
import io

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

            exctract_old_path = extract_path / uploaded_zip.name.split('.')[0] / 'OLD'
            exctract_new_path = extract_path / uploaded_zip.name.split('.')[0] / 'NEW'
            processor = CompareProcess(
                excel_file=str(excel_path),
                old_folder=str(exctract_old_path),
                new_folder=str(exctract_new_path)
            )
            results = processor.start()
            
            # Zip the output directory
            import base64
            import io
            
            output_dir = extract_path / "output"
            zip_data = None
            if output_dir.exists():
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(output_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zf.write(file_path, os.path.relpath(file_path, output_dir))
                zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
        except Exception as e:
            return render(request, 'FSCFAI_Compare/main.html', {'error': str(e)})
        finally:
            if 'processor' in locals():
                pass # processor.close() not implemented
            shutil.rmtree(request_temp, ignore_errors=True)

    return render(request, 'FSCFAI_Compare/main.html', {'results': results, 'zip_data': locals().get('zip_data')})