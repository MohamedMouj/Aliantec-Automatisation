import functools
import time
from django.db import transaction
from django.utils import timezone
from .models import ExecutionLog


def log_execution(application, action=None, project_name=None, filename=None):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            log_entry = ExecutionLog.objects.create(
                user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                application=application,
                action=action or view_func.__name__,
                project_name=project_name(request) if callable(project_name) else (project_name or ''),
                filename=filename(request) if callable(filename) else (filename or ''),
                status='RUNNING',
            )

            # Attach the log entry to the request so views can modify it
            request.execution_log = log_entry

            start_time = time.time()
            try:
                response = view_func(request, *args, **kwargs)
                
                # Only set to SUCCESS if the view hasn't manually marked it as FAILED or CANCELLED
                if log_entry.status == 'RUNNING':
                    log_entry.status = 'SUCCESS'
                
                log_entry.finished_at = timezone.now()
                log_entry.save(update_fields=['status', 'finished_at', 'error_message'])
                return response
            except Exception as exc:
                log_entry.status = 'FAILED'
                log_entry.finished_at = timezone.now()
                log_entry.error_message = str(exc)
                log_entry.save(update_fields=['status', 'finished_at', 'error_message'])
                raise

        return wrapper
    return decorator
