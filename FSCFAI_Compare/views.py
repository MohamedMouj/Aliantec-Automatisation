import io
import os
import shutil
import zipfile
import uuid
import base64
from pathlib import Path
 
from django.shortcuts import render
from django.http import FileResponse
 
from .helpers.process import CompareProcess
 
 
# --------------------------------------------------------------------------- #
#  Helper                                                                       #
# --------------------------------------------------------------------------- #
 
def _find_folder(root: Path, keyword: str) -> Path:
    candidates = [
        p for p in root.rglob("*")
        if p.is_dir() and keyword.upper() in p.name.upper()
    ]
    if not candidates:
        raise ValueError(
            f"No directory containing '{keyword}' found inside the ZIP. "
            f"Make sure the archive contains a folder with '{keyword}' in its name."
        )
    # min by path depth → shallowest = top-most match
    return min(candidates, key=lambda p: len(p.parts))
 
 
# --------------------------------------------------------------------------- #
#  View                                                                         #
# --------------------------------------------------------------------------- #
 
def index(request):
    if (
        request.method == "POST"
        and request.FILES.get("input_zip")
        and request.FILES.get("input_excel")
    ):
        uploaded_zip   = request.FILES["input_zip"]
        uploaded_excel = request.FILES["input_excel"]
        right=request.POST.get("new_ref_right")
 
        temp_base = Path(__file__).resolve().parent / "temp"
        temp_base.mkdir(exist_ok=True)
 
        request_temp = temp_base / str(uuid.uuid4())
        request_temp.mkdir(exist_ok=True)
 
        try:
            # ---------------------------------------------------------------- #
            #  1. Persist uploads to the isolated temp directory               #
            # ---------------------------------------------------------------- #
            excel_path = request_temp / uploaded_excel.name
            with open(excel_path, "wb+") as dst:
                for chunk in uploaded_excel.chunks():
                    dst.write(chunk)
 
            zip_path = request_temp / uploaded_zip.name
            with open(zip_path, "wb+") as dst:
                for chunk in uploaded_zip.chunks():
                    dst.write(chunk)
 
            # ---------------------------------------------------------------- #
            #  2. Extract the ZIP                                               #
            # ---------------------------------------------------------------- #
            extract_path = request_temp / "extracted"
            extract_path.mkdir(exist_ok=True)
 
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_path)
 
           
            extract_new_path = _find_folder(extract_path, "NEW") or extract_path
            extract_old_path = _find_folder(extract_path, "OLD") or extract_path
 
          
            output_dir = extract_path / "output"
            output_dir.mkdir(exist_ok=True)
 
            processor = CompareProcess(
                excel_file=str(excel_path),
                old_folder=str(extract_old_path),
                new_folder=str(extract_new_path),
                output_dir=str(output_dir),
                right=right
            )
            results = processor.start()
 
            if not results:
                return render(request, "FSCFAI_Compare/main.html", {
                    "results": results,
                    "zip_data": "",
                })
 
     
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname   = os.path.relpath(file_path, output_dir)
                        zf.write(file_path, arcname)
 
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")
 
            return render(request, "FSCFAI_Compare/main.html", {
                "zip_data": zip_data,
                "results":  results,
            })
 
        except ValueError as e:
            return render(request, "FSCFAI_Compare/main.html", {
                "error":    str(e),
                "zip_data": "",
                "results":  None,
            })
        except Exception as e:
            return render(request, "FSCFAI_Compare/main.html", {
                "error":    f"Processing error: {e}",
                "zip_data": "",
                "results":  None,
            })
        finally:
            shutil.rmtree(request_temp, ignore_errors=True)
 
    return render(request, "FSCFAI_Compare/main.html", {
        "zip_data": "",
        "results":  None,
    })

 