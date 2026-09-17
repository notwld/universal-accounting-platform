from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import FinanceSettings
from apps.finance.services.context import finance_tx


def _settings(org) -> FinanceSettings:
    settings = FinanceSettings.objects.filter(organization=org).first()
    if not settings:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return settings


def invalidate_approval(doc):
    if doc.status in (doc.Status.PENDING, doc.Status.APPROVED):
        doc.status = doc.Status.DRAFT
        doc.approved_by = ""
        type(doc).objects.filter(pk=doc.pk).update(status=doc.Status.DRAFT, approved_by="")


def require_approved_for_post(org, doc, *, skip_approval=False):
    if skip_approval:
        return
    settings = _settings(org)
    if settings.require_document_approval and doc.status != doc.Status.APPROVED:
        raise AuthAPIError("approval_required", "Document must be approved before posting")


def submit_document(*, user_id, org, model, doc_id):
    with finance_tx(user_id=user_id, organization_id=org.id):
        doc = model.objects.select_for_update().filter(id=doc_id, organization=org).first()
        if not doc:
            raise AuthAPIError("cross_organization", "Document not found")
        if doc.status == model.Status.POSTED:
            raise AuthAPIError("validation_error", "Posted documents cannot be submitted")
        doc.status = model.Status.PENDING
        doc.approved_by = ""
        model.objects.filter(pk=doc.pk).update(status=doc.status, approved_by="")
        return model.objects.get(pk=doc.pk)


def approve_document(*, user_id, org, model, doc_id):
    with finance_tx(user_id=user_id, organization_id=org.id):
        doc = model.objects.select_for_update().filter(id=doc_id, organization=org).first()
        if not doc:
            raise AuthAPIError("cross_organization", "Document not found")
        if doc.status != model.Status.PENDING:
            raise AuthAPIError("validation_error", "Only pending documents can be approved")
        settings = _settings(org)
        if doc.created_by and doc.created_by == user_id and not settings.allow_self_approve:
            raise AuthAPIError("self_approve_forbidden", "Preparer cannot approve this document")
        doc.status = model.Status.APPROVED
        doc.approved_by = user_id
        model.objects.filter(pk=doc.pk).update(status=doc.status, approved_by=user_id)
        return model.objects.get(pk=doc.pk)


def reject_document(*, user_id, org, model, doc_id, reason):
    if not (reason or "").strip():
        raise AuthAPIError("validation_error", "Rejection reason is required")
    with finance_tx(user_id=user_id, organization_id=org.id):
        doc = model.objects.select_for_update().filter(id=doc_id, organization=org).first()
        if not doc:
            raise AuthAPIError("cross_organization", "Document not found")
        if doc.status != model.Status.PENDING:
            raise AuthAPIError("validation_error", "Only pending documents can be rejected")
        doc.status = model.Status.DRAFT
        doc.approved_by = ""
        model.objects.filter(pk=doc.pk).update(status=doc.status, approved_by="")
        return model.objects.get(pk=doc.pk)
