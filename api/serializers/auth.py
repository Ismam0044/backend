from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .core import UserSerializer


class LoginSerializer(TokenObtainPairSerializer):
    """Stock SimpleJWT login, plus the serialized user embedded in the response so the
    app can bootstrap its UI (role, assigned_warehouses) without a second /auth/me call."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
