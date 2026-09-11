from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Restrict a view to users whose .role is in `roles`. Owner always passes."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.role == user.Role.OWNER or user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped
    return decorator


def warehouse_access_required(view_func):
    """Restrict a view to users assigned to the warehouse in `kwargs['warehouse_id']`."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        from core.models import Warehouse

        warehouse_id = kwargs.get("warehouse_id")
        if warehouse_id is not None:
            warehouse = Warehouse.objects.filter(pk=warehouse_id).first()
            if warehouse is None or not request.user.has_warehouse_access(warehouse):
                raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
