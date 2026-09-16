from rest_framework.permissions import BasePermission

from apps.authentication.models import AuthUser


class IsApplicationUser(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, AuthUser) and request.user.status == AuthUser.Status.ACTIVE
