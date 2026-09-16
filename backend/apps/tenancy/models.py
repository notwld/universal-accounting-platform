from django.db import models

from apps.authentication.ids import new_uuid


class Organization(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_organization"

    def __str__(self) -> str:
        return self.name


class Location(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="locations"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_location"

    def __str__(self) -> str:
        return f"{self.name} ({self.organization_id})"


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    id = models.CharField(primary_key=True, max_length=36, default=new_uuid, editable=False)
    user_id = models.CharField(max_length=36, db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="memberships"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    roles = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "organization"],
                name="uniq_membership_user_org",
            )
        ]
