from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, F
from django.shortcuts import render
from django.contrib.auth.models import User

from .models import ExecutionLog


@login_required
def dashboard(request):
    logs = ExecutionLog.objects.select_related('user')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    application_filter = request.GET.get('application')
    status_filter = request.GET.get('status')
    filename_filter = request.GET.get('filename')

    if date_from:
        logs = logs.filter(started_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(started_at__date__lte=date_to)
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if application_filter:
        logs = logs.filter(application__icontains=application_filter)
    if status_filter:
        logs = logs.filter(status=status_filter)
    if filename_filter:
        logs = logs.filter(filename__icontains=filename_filter)

    # Exclude incomplete entries (no filename = not a real execution)
    logs = logs.exclude(filename='')

    total_executions = logs.count()
    running = logs.filter(status='RUNNING').count()
    success = logs.filter(status='SUCCESS').count()
    failed = logs.filter(status='FAILED').count()
    average_time = logs.filter(finished_at__isnull=False).aggregate(avg=Avg(F('finished_at') - F('started_at')))

    avg_seconds = None
    if average_time.get('avg'):
        avg_seconds = int(average_time['avg'].total_seconds())

    by_application = (
        logs.values('application')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    by_user = (
        logs.values('user__username', 'user__first_name', 'user__last_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    recent_logs = logs[:20]

    context = {
        'logs': recent_logs,
        'total_executions': total_executions,
        'running': running,
        'success': success,
        'failed': failed,
        'average_time_seconds': avg_seconds,
        'by_application': list(by_application),
        'by_user': list(by_user),
        'users': User.objects.order_by('username'),
        'selected': {
            'date_from': date_from or '',
            'date_to': date_to or '',
            'user': user_filter or '',
            'application': application_filter or '',
            'status': status_filter or '',
            'filename': filename_filter or '',
        },
        'applications': [
            'Listes Types',
            'FSCFAI Compare',
            'Listing Devices',
            'Extraction VIN',
            'Extraction SM',
        ],
    }
    return render(request, 'analytics/dashboard.html', context)
