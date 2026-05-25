import io
import shutil
import uuid
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse
from .helpers.excel import ExcelParser


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
            parser.start(output_path=str(output_path))

            # Read the generated file into memory BEFORE the finally block deletes it
            with open(output_path, 'rb') as f:
                file_data = io.BytesIO(f.read())

            # Stream the file directly to the browser — no button, no session needed
            return FileResponse(
                file_data,
                as_attachment=True,
                filename=output_name,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

        except KeyError as e:
            return render(request, 'ExtractionVIN/main.html', {'error_msg': str(e)})
        except Exception as e:
            return render(request, 'ExtractionVIN/main.html', {'error_msg': f"Processing error: {e}"})
        finally:
            # Always close the parser and wipe the entire temp folder from disk
            if parser:
                parser.close()
            shutil.rmtree(request_temp, ignore_errors=True)

    return render(request, 'ExtractionVIN/main.html')
