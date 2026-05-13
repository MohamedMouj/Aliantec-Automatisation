import os
import shutil
import uuid
import json
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from .tables import UpdateTable, AdditionTable, DeletionTable
from django_tables2 import RequestConfig
from .services.orchestrator import Orchestrator 
from django.http import FileResponse, Http404
from django.conf import settings
from pathlib import Path

def get_safe_path(path_str):
    """
    Helper to add Windows Long Path prefix if needed.
    """
    abs_path = os.path.abspath(path_str)
    if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
        return '\\\\?\\' + abs_path
    return abs_path

def index(request):
    if request.method == 'POST' and request.FILES.get('pta_file') and request.FILES.get('zipped_fscfai'):
        pta_file = request.FILES['pta_file']
        zip_file = request.FILES['zipped_fscfai']

        session_id = uuid.uuid4().hex[:8]
        
        base_temp_dir = Path(__file__).resolve().parent / 'temp'
        session_dir = base_temp_dir / session_id
        
        safe_session_dir = Path(get_safe_path(str(session_dir)))
        os.makedirs(safe_session_dir, exist_ok=True)

        excel_path = safe_session_dir / pta_file.name
        with open(excel_path, 'wb+') as destination:
            for chunk in pta_file.chunks():
                destination.write(chunk)
            
        zip_path = safe_session_dir / zip_file.name
        with open(zip_path, 'wb+') as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)

        fscfai_data = None
        fscfai_json = request.POST.get('fscfai_json')
        if fscfai_json:
            try:
                fscfai_data = json.loads(fscfai_json)
            except Exception as e:
                return render(request, 'Listes_Types/index.html', {'error WITH JSON': str(e)})

        extracted_folder = get_safe_path(os.path.join(safe_session_dir, 'e'))
        os.makedirs(extracted_folder, exist_ok=True)

        # Get the parse direction from the checkbox
        parse_right = request.POST.get('parse_right') == 'on'

        try:
            orchestrator = Orchestrator(excel_path, zip_path, extracted_folder, fscfai_data=fscfai_data, parse_right=parse_right)
            results, error = orchestrator.process_all()

            if error:
                return render(request, 'Listes_Types/index.html', {'error': error})

            zip_output_name = results.get("download_name")
            final_zip_name = f"{session_id}.zip"
            if zip_output_name != 'N/A':
                source_zip = os.path.join(safe_session_dir, zip_output_name)
                target_zip = os.path.join(base_temp_dir, final_zip_name)
                if os.path.exists(source_zip):
                    shutil.move(source_zip, target_zip)

            table_updates = UpdateTable(results["all_grid_data"])
            table_deletions = DeletionTable(results["all_to_delete"])
            table_additions = AdditionTable(results["all_to_add"])
            
            RequestConfig(request, paginate=False).configure(table_updates)
            RequestConfig(request, paginate=False).configure(table_deletions)
            RequestConfig(request, paginate=False).configure(table_additions)
            
            context = {
                'table_updates': table_updates,
                'table_additions': table_additions,
                'table_deletions': table_deletions,
                'summary': results["total_summary"],
                'output_path': final_zip_name,
                'processed': True,
                'xml_count': results["total_summary"].get("xml_count", []),
            }

            return render(request, 'Listes_Types/index.html', context)

        except Exception as e:
            return render(request, 'Listes_Types/index.html', {'error': str(e)})

        finally:
            try:
                if os.path.exists(safe_session_dir):
                    shutil.rmtree(safe_session_dir, ignore_errors=True)
                if os.path.exists(extracted_folder):
                    shutil.rmtree(extracted_folder, ignore_errors=True)
            except:
                pass

    return render(request, 'Listes_Types/index.html')

def download_file(request, filename):
    # Sanitize filename to remove trailing slashes from the URL pattern
    filename = filename.rstrip('/')
    base_temp_dir = Path(__file__).resolve().parent / 'temp'
    # Use long path prefix for file access
    file_path = get_safe_path(str(base_temp_dir / filename))

    if not os.path.exists(file_path):
        raise Http404(f"The file does not exist at {file_path}")

    content_type = 'application/zip' if filename.endswith('.zip') else 'application/octet-stream'
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass
    return response
