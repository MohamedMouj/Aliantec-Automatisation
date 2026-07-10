import os
import traceback
import uuid
import zipfile
import base64
import io
from pathlib import Path

from django.shortcuts import redirect, render

from .helpers.xml_parser import xml_parser
from .services.orchestrator import Orchestrator


def get_safe_path(path_str):
    abs_path = os.path.abspath(path_str)
    if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
        return '\\\\?\\' + abs_path
    return abs_path


def index(request):
    if request.method == 'POST' and request.FILES.get('zipped_fscfai'):
        zip_file = request.FILES['zipped_fscfai']

        session_id = uuid.uuid4().hex[:8]
        base_temp_dir = Path(__file__).resolve().parent / 'temp'
        session_dir = base_temp_dir / session_id

        safe_session_dir = Path(get_safe_path(str(session_dir)))
        os.makedirs(safe_session_dir, exist_ok=True)

        zip_path = safe_session_dir / zip_file.name
        with open(zip_path, 'wb+') as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)

        extracted_folder = get_safe_path(os.path.join(safe_session_dir, 'e'))
        os.makedirs(extracted_folder, exist_ok=True)

        try:
            orchestrator = Orchestrator(zip_path, extracted_folder)
            results, error = orchestrator.process_all()

            if error:
                return render(request, 'Listes_Types/DAD_DAG/index.html', {'error': error})

            # --- BUG 1 FIX ---
            # context.unsured_refs is now a dict:
            #   {current_ref: {'candidates': (old_filename, [(cand_filename, score), ...]), 'xml_paths': set()}}
            # Transform into template-ready review items.
            raw_unsured = results.get('unsured_refs', {})
            review_items = []

            for idx, (current_ref, data) in enumerate(raw_unsured.items()):
                xml_paths = list(data.get('xml_paths', []))
                candidates_data = data.get('candidates')   # tuple from FSCF.start()

                if not current_ref or not xml_paths or not candidates_data:
                    continue
                if not isinstance(candidates_data, tuple) or len(candidates_data) < 2:
                    continue

                old_xml_filename, candidate_list = candidates_data
                if not candidate_list:
                    continue

                # Build structured candidate dicts for the template
                candidates = []
                for cand_filename, score in candidate_list:
                    if cand_filename:
                        candidates.append({
                            'value': cand_filename,
                            'description': cand_filename,
                            'score': round(float(score), 1),
                        })

                if not candidates:
                    continue

                candidates.sort(key=lambda c: c['score'], reverse=True)
                best = candidates[0]

                review_items.append({
                    'item_id': f'item-{idx}',
                    'current_ref': current_ref,
                    # Human-readable header in the audit card
                    'current_ref_description': old_xml_filename,
                    'xml_paths': xml_paths,
                    'old_xml_path': old_xml_filename,
                    'candidates': candidates,
                    'automated_choice': best['value'],
                    'automated_description': None, 
                    'score': best['score'],
                })

            if review_items:
                request.session['dad_dag_reviews'] = review_items
                request.session['dad_dag_session_id'] = session_id

                return render(request, 'Listes_Types/DAD_DAG/audit_review.html', {
                    'unsured_refs': review_items,
                    'audit_count': len(review_items),   # BUG 5 FIX: pass audit_count
                    'summary': results.get('summary', {}),
                    'session_id': session_id,
                })
            else:
                return render(request, 'Listes_Types/DAD_DAG/index.html', {
                    'error': 'No unresolved references required user review.',
                })

        except Exception as exc:
            return render(request, 'Listes_Types/DAD_DAG/index.html', {
                'error': f"{exc}\n{traceback.format_exc()}",
            })

    return render(request, 'Listes_Types/DAD_DAG/index.html')


def finalize(request):
    if request.method != 'POST':
        return redirect('dad_dag')

    pending_reviews = request.session.pop('dad_dag_reviews', [])
    if not pending_reviews:
        return redirect('dad_dag')

    updates_by_file = {}

    for item in pending_reviews:
        choice_key = f"choice_{item['item_id']}"
        selected_ref = request.POST.get(choice_key)
        if not selected_ref or selected_ref == '__SKIP__':
            continue

        xml_paths = item.get('xml_paths', [])
        for xml_path in xml_paths:
            if not xml_path:
                continue

            # --- BUG 3 FIX: update_data is now a plain dict, not a ('type', dict) tuple ---
            if xml_path not in updates_by_file:
                updates_by_file[xml_path] = []
            updates_by_file[xml_path].append({
                'current_ref': item['current_ref_description'],
                'new_ref': selected_ref,
            })

    versioned_files = []
    finalized_updates = []
    skipped_updates = []    # Refs whose 10-digit number was not found in the target XML

    # Process each file once with all its updates
    for xml_path, updates_list in updates_by_file.items():
        safe_xml_path = get_safe_path(xml_path)
        if not os.path.exists(safe_xml_path):
            continue

        parser = xml_parser(safe_xml_path, None)
        parser.parse_xml()
        file_updated = False

        for update_data in updates_list:
            current_ref = update_data['current_ref']
            new_ref = update_data['new_ref']

            # NEW: Verify the ref actually lives in THIS specific XML file before writing.
            # A ref may be shared across multiple .list files, so we must confirm existence
            # per-file rather than blindly updating every file that was processed.
            if not parser.is_ref_exist(current_ref):
                skipped_updates.append({
                    'xml_path': safe_xml_path,
                    'current_ref': current_ref,
                    'new_ref': new_ref,
                })
                continue

            updated, _ = parser.update_reference(current_ref, new_ref)
            if updated:
                file_updated = True
                finalized_updates.append({
                    'xml_path': safe_xml_path,
                    'current_ref': current_ref,
                    'new_ref': new_ref,
                })

        if file_updated:
            versioned_path = parser.save_versioned_file()
            if versioned_path and os.path.exists(versioned_path):
                versioned_files.append(versioned_path)

    completion_message = 'Review completed.'
    has_download = False
    zip_b64 = None
    zip_name = None

    if versioned_files:
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in set(versioned_files):
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zf.write(file_path, arcname=arcname)

            zip_buffer.seek(0)
            zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            zip_name = f"dad_dag_updated_{uuid.uuid4().hex[:8]}.zip"
            has_download = True
        except Exception:
            pass

    return render(request, 'Listes_Types/DAD_DAG/index.html', {
        'success': completion_message,
        'processed': True,
        'finalized_updates': finalized_updates,
        'skipped_updates': skipped_updates,
        'total_finalized': len(finalized_updates),
        'total_skipped': len(skipped_updates),
        'summary': {
            'total': len(finalized_updates),
            'matches': len(finalized_updates),
            'updates': len(finalized_updates),
        },
        'xml_count': len(updates_by_file),
        'table_updates': None,
        'has_download': has_download,
        'zip_b64': zip_b64,
        'zip_name': zip_name,
    })
