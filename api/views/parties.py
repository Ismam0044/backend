from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from parties.models import Party

from api.serializers.parties import PartySerializer


class PartyListView(ListAPIView):
    """GET /parties/?q=&type= - customer/supplier picker (POS/Purchase) and the
    parties list screen. Built on Party.objects.with_balance() (reused as-is)."""

    serializer_class = PartySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        request = self.request
        parties = Party.objects.filter(is_active=True).with_balance()

        q = request.query_params.get("q", "").strip()
        if q:
            parties = parties.filter(name__icontains=q)

        party_type = request.query_params.get("type")
        if party_type:
            parties = parties.filter(type=party_type)

        return parties.order_by("name")[:50]
