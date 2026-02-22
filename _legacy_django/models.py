from django.db import models


class OptimizationRun(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    template_type = models.CharField(max_length=64, default='cutting')
    sense = models.CharField(max_length=16, default='minimize')
    status = models.CharField(max_length=32, default='pending')

    def __str__(self):
        return f"{self.template_type}:{self.sense}:{self.status}"
