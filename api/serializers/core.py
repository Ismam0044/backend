from rest_framework import serializers

from core.models import User, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Warehouse
        fields = ["id", "name", "address", "type", "type_display", "is_active"]


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    assigned_warehouses = WarehouseSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "phone",
            "role", "role_display", "assigned_warehouses",
        ]
