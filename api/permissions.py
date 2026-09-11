"""DRF permission classes wrapping the same rules as core.permissions'
function-view decorators - User.Role / User.has_warehouse_access() stay the
single source of truth; these are thin adapters for class-based API views."""

from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """Restrict a view to users whose .role is in view.allowed_roles. Owner always passes.
    Mirrors core.permissions.role_required's rule (duplicated, not imported, since a
    decorator and a BasePermission have incompatible call signatures - both read the
    same User.Role enum and .role field)."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        allowed_roles = getattr(view, "allowed_roles", ())
        return user.role == user.Role.OWNER or user.role in allowed_roles


class HasWarehouseAccess(BasePermission):
    """Object-level check delegating to User.has_warehouse_access() - the same method
    core.permissions.warehouse_access_required uses for the HTMX views."""

    def has_object_permission(self, request, view, obj):
        from core.models import Warehouse

        warehouse = obj if isinstance(obj, Warehouse) else getattr(obj, "warehouse", None)
        return warehouse is None or request.user.has_warehouse_access(warehouse)
