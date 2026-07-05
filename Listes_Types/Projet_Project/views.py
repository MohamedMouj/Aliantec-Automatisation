import base64
import os
import shutil
import uuid
import json
from django.shortcuts import render
from pathlib import Path
from django_tables2 import RequestConfig
from .service.orchestrator import Orchestrator
from ..tables import UpdateTable, DeletionTable, AdditionTable
from analytics.decorators import log_execution


def get_safe_path(path_str):
    """
    Add Windows Long Path prefix if needed.
    On Linux/Hostinger VPS this is a no-op.
    """
    abs_path = os.path.abspath(path_str)
    if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
        return '\\\\?\\' + abs_path
    return abs_path


@log_execution('Listes Types', action='Project Project Update', project_name=lambda request: '', filename=lambda request: request.FILES.get('zipped_fscfai').name if request.FILES.get('zipped_fscfai') else '')
def projet_project(request):
    if request.method == 'POST' and request.FILES.get('zipped_fscfai'):
        zip_file = request.FILES['zipped_fscfai']
        old_project_name = str(request.POST.get('old_project', '').strip())
        new_project_name = str(request.POST.get('new_project', '').strip())

        session_id = uuid.uuid4().hex[:8]

        base_temp_dir = Path(__file__).resolve().parent / 'temp'
        session_dir = base_temp_dir / session_id

        safe_session_dir = Path(get_safe_path(str(session_dir)))
        os.makedirs(safe_session_dir, exist_ok=True)

    

        # Save uploaded ZIP file
        zip_path = safe_session_dir / zip_file.name
        with open(zip_path, 'wb+') as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)

      
        extracted_folder = get_safe_path(os.path.join(safe_session_dir, 'e'))
        os.makedirs(extracted_folder, exist_ok=True)


        try:
            orchestrator = Orchestrator(extracted_folder, str(zip_path), old_project_name, new_project_name)
            results, error = orchestrator.process_all()

            if error:
                return render(request, 'Listes_Types/Projet_Project/index.html', {'error': error})

            zip_output_name = results.get('download_name')
            zip_b64 = None
            final_zip_name = None
            if zip_output_name and zip_output_name != 'N/A':
                source_zip = os.path.join(safe_session_dir, zip_output_name)
                if os.path.exists(source_zip):
                    with open(source_zip, 'rb') as f:
                        zip_b64 = base64.b64encode(f.read()).decode('ascii')
                    final_zip_name = f"{session_id}.zip"

            table_updates = UpdateTable(results.get('all_grid_data', []))
            table_additions  = AdditionTable(results.get('addition_data', []))
            table_deletions  = DeletionTable(results.get('deletion_data', []))

            RequestConfig(request, paginate=False).configure(table_updates)
            RequestConfig(request, paginate=False).configure(table_additions)
            RequestConfig(request, paginate=False).configure(table_deletions)

            context = {
                'table_updates':    table_updates,
                'summary':          results['total_summary'],
                'zip_b64':          zip_b64,
                'zip_name':         final_zip_name,
                'has_download':     zip_b64 is not None,
                'processed':        True,
                'xml_count':        results['total_summary'].get('xml_count', []),
            }

            return render(request, 'Listes_Types/Projet_Project/index.html', context)

        except Exception as e:
            return render(request, 'Listes_Types/Projet_Project/index.html', {'error': str(e)})

        finally:
            try:
                shutil.rmtree(safe_session_dir, ignore_errors=True)
                if os.path.exists(extracted_folder):
                    shutil.rmtree(extracted_folder, ignore_errors=True)
            except Exception:
                pass

    return render(request, 'Listes_Types/Projet_Project/index.html')


