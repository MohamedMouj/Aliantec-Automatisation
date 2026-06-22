import io
import os
import shutil
import zipfile
import uuid
import base64
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse
from .helpers.process import CompareProcess


def index(request):
    if request.method == 'POST' and request.FILES.get('input_zip') and request.FILES.get('input_excel'):
        uploaded_zip = request.FILES['input_zip']
        uploaded_excel = request.FILES['input_excel']

        temp_base = Path(__file__).resolve().parent / 'temp'
        temp_base.mkdir(exist_ok=True)

        request_temp = temp_base / str(uuid.uuid4())
        request_temp.mkdir(exist_ok=True)

        try:
            # Save uploaded Excel file
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, 'wb+') as destination:
                for chunk in uploaded_excel.chunks():
                    destination.write(chunk)

            # Save uploaded ZIP file
            zip_path = request_temp / uploaded_zip.name
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_zip.chunks():
                    destination.write(chunk)

            # Extract the ZIP
            extract_path = request_temp / 'extracted'
            extract_path.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
            extract_old_path = None
            extract_new_path = None
            
            # Find the NEW and OLD folders safely, regardless of root folder name
            for path in extract_path.rglob('*'):
                if path.is_dir():
                    if 'NEW' in path.name.upper() and extract_new_path is None:
                        extract_new_path = path
                    elif 'OLD' in path.name.upper() and extract_old_path is None:
                        extract_old_path = path
            
            if extract_old_path is None:
                extract_old_path = Path()
            if extract_new_path is None:
                extract_new_path = Path()
            

            processor = CompareProcess(
                excel_file=str(excel_path),
                old_folder=str(extract_old_path),
                new_folder=str(extract_new_path),
            )
            results = processor.start()

            # Build the output ZIP in memory
            output_dir = extract_path / 'output'
            if not output_dir.exists():
                return render(request, 'FSCFAI_Compare/main.html', {
                    'error': 'Processing completed but no output directory was produced.'
                })

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zf.write(file_path, os.path.relpath(file_path, output_dir))
            
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            
            return render(request, 'FSCFAI_Compare/main.html', {
                'zip_data': zip_data,
                'results': results
            })

        except Exception as e:
            return render(request, 'FSCFAI_Compare/main.html', {'error': str(e)})

        finally:
            # Always wipe the entire temp folder from disk
            shutil.rmtree(request_temp, ignore_errors=True)

    return render(request, 'FSCFAI_Compare/main.html')
