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

        # 1. Use a very short session ID to save path length
        session_id = uuid.uuid4().hex[:8]
        
        # 2. Use very short folder names ('t' instead of 'temp')
        base_temp_dir = Path(settings.BASE_DIR).parent / 'Listes_Types' / 't'
        session_dir = base_temp_dir / session_id
        
        # Ensure we use the long path prefix for all OS operations
        safe_session_dir = get_safe_path(str(session_dir))
        os.makedirs(safe_session_dir, exist_ok=True)

        # 3. Save Excel file
        fs = FileSystemStorage(location=safe_session_dir)
        pta_path = fs.save(pta_file.name, pta_file)
        pta_full_path = fs.path(pta_path)

        # 4. Save uploaded ZIP
        zip_path = fs.save(zip_file.name, zip_file)
        zip_full_path = fs.path(zip_path)

        fscfai_data = None
        fscfai_json = request.POST.get('fscfai_json')
        if fscfai_json:
            try:
                fscfai_data = json.loads(fscfai_json)
            except:
                pass

        # 5. Shorten extraction folder name ('e' instead of 'extracted')
        extracted_folder = get_safe_path(os.path.join(safe_session_dir, 'e'))
        os.makedirs(extracted_folder, exist_ok=True)

        try:
            orchestrator = Orchestrator(pta_full_path, zip_full_path, extracted_folder, fscfai_data=fscfai_data)
            results, error = orchestrator.process_all()

            if error:
                return render(request, 'Listes_Types/index.html', {'error': error})

            # Prepare tables
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
                'output_path': f"{session_id}/{results['download_name']}",
                'processed': True,
                'xml_count': results["total_summary"].get("xml_count", []),
            }

            return render(request, 'Listes_Types/index.html', context)

        except Exception as e:
            # import traceback
            # traceback.print_exc()
            return render(request, 'Listes_Types/index.html', {'error': str(e)})

        finally:
            # Clean up
            try:
                if os.path.exists(extracted_folder):
                    shutil.rmtree(extracted_folder, ignore_errors=True)
                versioned_dir = os.path.join(safe_session_dir, 'v')
                if os.path.exists(versioned_dir):
                    shutil.rmtree(versioned_dir, ignore_errors=True)
            except:
                pass

    return render(request, 'Listes_Types/index.html')

def download_file(request, filename):
    base_temp_dir = Path(settings.BASE_DIR).parent / 'Listes_Types' / 't'
    # Use long path prefix for file access
    file_path = get_safe_path(str(base_temp_dir / filename))

    if not os.path.exists(file_path):
        raise Http404("The file does not exist.")

    content_type = 'application/zip' if filename.endswith('.zip') else 'application/octet-stream'
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'
    return response
