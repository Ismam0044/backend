def resolve_warehouse(queryset, raw_id):
    """Safely look up a warehouse by a possibly-empty/invalid raw id from a form."""
    if not raw_id:
        return None
    try:
        return queryset.filter(pk=raw_id).first()
    except (ValueError, TypeError):
        return None


def accessible_warehouses(user):
    """Warehouses this user may operate in - all active ones for Owner/unassigned staff,
    otherwise only their assigned set."""
    from core.models import Warehouse

    if user.role == user.Role.OWNER or not user.assigned_warehouses.exists():
        return Warehouse.objects.filter(is_active=True)
    return user.assigned_warehouses.filter(is_active=True)
