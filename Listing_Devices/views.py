import os
import shutil
import zipfile
import io
import uuid
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse
from .helpers.process import DevicesProcess
from analytics.decorators import log_execution

@log_execution('Listing Devices', action='Device Listing', project_name=lambda request: '', filename=lambda request: request.FILES.get('input_zip').name if request.FILES.get('input_zip') else '')
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
                for zip_info in zip_ref.filelist:
                    if zip_info.is_dir():
                        continue
                        
                    # Reconstruct the folder path
                    rel_dir = Path(zip_info.filename).parent
                    target_dir = extract_path / rel_dir
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Handle the long filename issue
                    original_name = Path(zip_info.filename).name
                    if len(original_name) > 50:
                        stem = Path(original_name).stem
                        ext = Path(original_name).suffix
                        # Many FSCFAI files have lots of extra tags after a space
                        if " " in stem:
                            stem = stem.split(" ")[0]
                        # Hard truncate if it's still insanely long
                        if len(stem) > 60:
                            stem = stem[:60]
                        new_name = stem + ext
                    else:
                        new_name = original_name
                        
                    # Extract to the modified path
                    target_path = target_dir / new_name
                    with zip_ref.open(zip_info) as source, open(str(target_path), "wb") as target:
                        shutil.copyfileobj(source, target)
            
            
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
