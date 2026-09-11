def resolve_warehouse(queryset, raw_id):
    """Safely look up a warehouse by a possibly-empty/invalid raw id from a form."""
    if not raw_id:
        return None
    try:
        return queryset.filter(pk=raw_id).first()
    except (ValueError, TypeError):
        return None
