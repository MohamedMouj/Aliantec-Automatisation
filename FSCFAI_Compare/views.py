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
    """
    Return the *shallowest* directory under *root* whose name contains
    *keyword* (case-insensitive).
 
    WHY SHALLOWEST:
      On Linux the filesystem is case-sensitive and `Path.rglob()` yields
      entries in inode order, which is non-deterministic across runs and
      machines.  A ZIP like::
 
          root/
            NEW/          ← correct target
              subfolder_NEW/   ← would also match 'NEW'
 
      could make the original first-match logic pick `subfolder_NEW` instead
      of `NEW`.  Taking the entry with the fewest path components always
      selects the top-most (intended) folder regardless of traversal order.
 
    WHY NOT Path() AS FALLBACK:
      The original code fell back to ``Path()`` when no folder was found.
      On Linux, ``Path()`` resolves to the process's current working
      directory, which *always* exists.  ``CompareProcess`` would then
      silently read from cwd, producing garbage results with no error.
      We raise ``ValueError`` instead so the ``except`` block surfaces a
      clear message to the user.
    """
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
 
            # ---------------------------------------------------------------- #
            #  3. Locate NEW / OLD folders                                      #
            #                                                                    #
            #  _find_folder raises ValueError with a user-friendly message if   #
            #  either folder is missing — no more silent Path() / cwd fallback. #
            # ---------------------------------------------------------------- #
            extract_new_path = _find_folder(extract_path, "NEW")
            extract_old_path = _find_folder(extract_path, "OLD")
 
            # ---------------------------------------------------------------- #
            #  4. Run the comparison                                             #
            # ---------------------------------------------------------------- #
            output_dir = extract_path / "output"
            output_dir.mkdir(exist_ok=True)
 
            processor = CompareProcess(
                excel_file=str(excel_path),
                old_folder=str(extract_old_path),
                new_folder=str(extract_new_path),
                output_dir=str(output_dir),
            )
            results = processor.start()
 
            if not results:
                return render(request, "FSCFAI_Compare/main.html", {
                    "results": results,
                    "zip_data": "",
                })
 
            # ---------------------------------------------------------------- #
            #  5. Build output ZIP                                              #
            #                                                                    #
            #  The ZIP is built into a BytesIO buffer so the temp directory     #
            #  can be wiped in `finally` before the response leaves.            #
            #  base64 encoding is preserved because the template uses it for    #
            #  a client-side JS blob download — do not remove it.               #
            #                                                                    #
            #  Memory note: base64 adds ~33 % overhead on top of the raw ZIP.  #
            #  For very large result sets consider switching the template to     #
            #  a FileResponse endpoint, but that requires a template change     #
            #  outside the scope of this fix.                                   #
            # ---------------------------------------------------------------- #
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
            # Missing NEW / OLD folder — user-facing message
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
            # Always wipe the entire per-request temp directory
            shutil.rmtree(request_temp, ignore_errors=True)
 
    return render(request, "FSCFAI_Compare/main.html", {
        "zip_data": "",
        "results":  None,
    })
 