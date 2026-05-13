import os
import shutil
import uuid
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse, Http404
from .helpers.excel import ExcelParser


def index(request):
    results = None
    error_msg = None
    download_name = None

    if request.method == 'POST' and request.FILES.get('input_excel'):
        uploaded_excel = request.FILES['input_excel']

        temp_base = Path(__file__).resolve().parent / 'temp'
        temp_base.mkdir(exist_ok=True)

        request_temp = temp_base / str(uuid.uuid4())
        request_temp.mkdir(exist_ok=True)

        parser = None
        try:
            # Save uploaded file
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, 'wb+') as destination:
                for chunk in uploaded_excel.chunks():
                    destination.write(chunk)

            # Process
            parser = ExcelParser(str(excel_path))
            parser.load_excel()

            output_name = f"output_{uploaded_excel.name}"
            output_path = request_temp / output_name
            results, _ = parser.start(output_path=str(output_path))

            # Store in session for download
            request.session['extraction_sm_download'] = str(output_path)
            request.session['extraction_sm_download_name'] = output_name

            download_name = output_name

        except KeyError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Processing error: {e}"
        finally:
            if parser:
                parser.close()

    return render(request, 'Extraction_SM/main.html', {
        'results': results,
        'error_msg': error_msg,
        'download_name': download_name,
    })


def download_file(request):
    file_path = request.session.get('extraction_sm_download')
    file_name = request.session.get('extraction_sm_download_name', 'output.xlsx')

    if not file_path or not os.path.exists(file_path):
        raise Http404("File not found or session expired.")

    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=file_name,
    )

    request.session.pop('extraction_sm_download', None)
    request.session.pop('extraction_sm_download_name', None)

    return response
