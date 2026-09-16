from django.contrib import admin

from apps.tenancy.models import Location, Membership, Organization

admin.site.register(Organization)
admin.site.register(Location)
admin.site.register(Membership)
