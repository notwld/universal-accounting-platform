from apps.finance.models import DocumentSequence


def next_document_number(organization, document_type: str, prefix: str) -> str:
    seq, _ = DocumentSequence.objects.get_or_create(
        organization=organization,
        document_type=document_type,
        series="default",
        defaults={"prefix": prefix, "next_number": 1},
    )
    seq = DocumentSequence.objects.select_for_update().get(pk=seq.pk)
    number = seq.next_number
    seq.next_number = number + 1
    seq.save(update_fields=["next_number"])
    return f"{seq.prefix}{number:04d}"


def next_journal_number(organization) -> str:
    return next_document_number(organization, "journal", "JE-")
