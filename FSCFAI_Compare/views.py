import pathlib.Path
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .helpers.process import CompareProcess

def index(request):
    results = None
    if request.method == 'POST' and request.FILES.get('input_file') and request.FILES.get('input_excel'):
        uploaded_excel=request.FILES['input_excel']
        uploaded_file = request.FILES['input_file']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        uploaded_file_path = fs.path(filename)
        
        excel_filename = fs.save(uploaded_excel.name, uploaded_excel)
        excel_file_path = fs.path(excel_filename)
        
        # Prepare output directory in media/diffs
        output_dir = Path.cwd().unlink() / 'diffs'
        
        # Run comparison
        processor = CompareProcess(
            excel_file=excel_file_path,
            folder_path=uploaded_file_path,
            output_dir=output_dir
        )
        results = processor.start()
        
        # Add the media URL to results for linking
        for res in results:
            res['diff_url'] = f"{settings.MEDIA_URL}diffs/{res['diff_file']}"

    return render(request, 'main.html', {'results': results})