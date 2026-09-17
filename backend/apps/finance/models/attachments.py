from django.conf import settings
from django.db import models

from apps.authentication.ids import new_uuid


def _upload_to(instance, filename):
    return f"finance/{instance.organization_id}/{instance.id}/{filename}"


class FinanceAttachment(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey("tenancy.Organization", on_delete=models.PROTECT)
    object_type = models.CharField(max_length=32)
    object_id = models.CharField(max_length=36)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    file = models.FileField(upload_to=_upload_to)
    uploaded_by = models.CharField(max_length=36, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_attachment"


ALLOWED_TYPES = frozenset(
    {"application/pdf", "image/png", "image/jpeg", "image/webp"}
)
MAX_BYTES = getattr(settings, "FINANCE_ATTACHMENT_MAX_BYTES", 10 * 1024 * 1024)
