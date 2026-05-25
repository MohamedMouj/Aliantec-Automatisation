import io
import os
import shutil
import uuid
import json
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.conf import settings
from pathlib import Path
from .tables import UpdateTable, AdditionTable, DeletionTable
from django_tables2 import RequestConfig
from .services.orchestrator import Orchestrator


def get_safe_path(path_str):
    """
    Add Windows Long Path prefix if needed.
    On Linux/Hostinger VPS this is a no-op.
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

        # Save uploaded PTA (Excel) file
        excel_path = safe_session_dir / pta_file.name
        with open(excel_path, 'wb+') as destination:
            for chunk in pta_file.chunks():
                destination.write(chunk)

        # Save uploaded ZIP file
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

        zip_buffer = None

        try:
            orchestrator = Orchestrator(
                excel_path, zip_path, extracted_folder,
                fscfai_data=fscfai_data, parse_right=parse_right,
            )
            results, error = orchestrator.process_all()

            if error:
                return render(request, 'Listes_Types/index.html', {'error': error})

            zip_output_name = results.get('download_name')
            if zip_output_name and zip_output_name != 'N/A':
                source_zip = os.path.join(safe_session_dir, zip_output_name)
                if os.path.exists(source_zip):
                    # Read the output ZIP into memory so we can delete the temp dir immediately
                    with open(source_zip, 'rb') as f:
                        zip_buffer = io.BytesIO(f.read())
                    final_zip_name = f"{session_id}.zip"
                else:
                    zip_buffer = None
                    final_zip_name = None
            else:
                zip_buffer = None
                final_zip_name = None

            # Build result tables
            table_updates   = UpdateTable(results['all_grid_data'])
            table_deletions = DeletionTable(results['all_to_delete'])
            table_additions = AdditionTable(results['all_to_add'])

            RequestConfig(request, paginate=False).configure(table_updates)
            RequestConfig(request, paginate=False).configure(table_deletions)
            RequestConfig(request, paginate=False).configure(table_additions)

            # Store the ZIP buffer in the session as base64 so the auto-download
            # endpoint can serve it without hitting the filesystem again.
            if zip_buffer:
                import base64
                request.session['listes_types_zip_data'] = base64.b64encode(
                    zip_buffer.getvalue()
                ).decode('utf-8')
                request.session['listes_types_zip_name'] = final_zip_name

            context = {
                'table_updates':    table_updates,
                'table_additions':  table_additions,
                'table_deletions':  table_deletions,
                'summary':          results['total_summary'],
                'has_download':     zip_buffer is not None,
                'processed':        True,
                'xml_count':        results['total_summary'].get('xml_count', []),
                'output_path':      final_zip_name,
            }

            return render(request, 'Listes_Types/index.html', context)

        except Exception as e:
            return render(request, 'Listes_Types/index.html', {'error': str(e)})

        finally:
            # Always wipe the entire session temp directory from disk
            try:
                shutil.rmtree(safe_session_dir, ignore_errors=True)
                if os.path.exists(extracted_folder):
                    shutil.rmtree(extracted_folder, ignore_errors=True)
            except Exception:
                pass

    return render(request, 'Listes_Types/index.html')


def download_file(request):
    """
    Serves the output ZIP that was stored in the session after processing.
    Called automatically by a JS trigger in the results template — no button needed.
    Clears the session entry immediately after streaming to free memory.
    """
    import base64

    zip_b64  = request.session.get('listes_types_zip_data')
    zip_name = request.session.get('listes_types_zip_name', 'output.zip')

    if not zip_b64:
        raise Http404('No file available. The session may have expired — please re-process.')

    # Decode from session back to bytes
    file_data = io.BytesIO(base64.b64decode(zip_b64))

    # Clear session entries immediately — one-time download
    request.session.pop('listes_types_zip_data', None)
    request.session.pop('listes_types_zip_name', None)

    return FileResponse(
        file_data,
        as_attachment=True,
        filename=zip_name,
        content_type='application/zip',
    )
