from django.db import models
from django.contrib.auth.models import User


class ExecutionLog(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='execution_logs')
    application = models.CharField(max_length=100)
    action = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255, blank=True, default='')
    filename = models.CharField(max_length=255, blank=True, default='')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Execution Log'
        verbose_name_plural = 'Execution Logs'

    def duration_seconds(self):
        if not self.finished_at:
            return None
        return int((self.finished_at - self.started_at).total_seconds())

    def duration_display(self):
        seconds = self.duration_seconds()
        if seconds is None:
            return 'Running'
        if seconds < 60:
            return f'{seconds}s'
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f'{minutes}m {secs}s'
        hours, mins = divmod(minutes, 60)
        return f'{hours}h {mins}m'

    def __str__(self):
        return f'{self.application} - {self.action} - {self.status}'
