import base64
import shutil
import uuid
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render
from .helpers.excel import ExcelParser
from analytics.decorators import log_execution


@log_execution('Extraction VIN', action='Excel Extraction', project_name=lambda request: '', filename=lambda request: request.FILES.get('input_excel').name if request.FILES.get('input_excel') else '')
def index(request):
    if request.method == 'POST' and request.FILES.get('input_excel'):
        uploaded_excel = request.FILES['input_excel']

        temp_base = Path(__file__).resolve().parent / 'temp'
        temp_base.mkdir(exist_ok=True)

        request_temp = temp_base / str(uuid.uuid4())
        request_temp.mkdir(exist_ok=True)

        parser = None
        try:
            # Save the uploaded file to the temp directory
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, 'wb+') as destination:
                for chunk in uploaded_excel.chunks():
                    destination.write(chunk)

            # Process the file
            parser = ExcelParser(str(excel_path))
            parser.load_excel()

            output_name = f"output_{uploaded_excel.name}"
            output_path = request_temp / output_name
            results, _ = parser.start(output_path=str(output_path))

            # Read the generated file into memory BEFORE the finally block deletes it
            with open(output_path, 'rb') as f:
                file_bytes = f.read()

            # Respond with JSON: the results table data + the file itself
            # (base64-encoded) in a single round trip. This lets the
            # frontend know precisely when processing is done (so it can
            # hide the spinner immediately, instead of guessing), and lets
            # it trigger the download itself via a Blob, without needing a
            # second endpoint or server-side session state.
            return JsonResponse({
                'success': True,
                'results': results,
                'download_name': output_name,
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'file_data': base64.b64encode(file_bytes).decode('ascii'),
            })

        except KeyError as e:
            return JsonResponse({'success': False, 'error_msg': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error_msg': f"Processing error: {e}"}, status=500)
        finally:
            if parser:
                parser.close()
            shutil.rmtree(request_temp, ignore_errors=True)

    return render(request, 'ExtractionVIN/main.html')
