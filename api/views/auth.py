from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.serializers.auth import LoginSerializer
from api.serializers.core import UserSerializer


class LoginView(TokenObtainPairView):
    """POST username/password -> {access, refresh, user}. Goes through Django's
    authenticate() via SimpleJWT's serializer, so django-axes brute-force lockout
    protection applies here automatically, same as the web app's /login/."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class LogoutView(APIView):
    """POST {refresh} -> blacklists that refresh token, logging out just this device."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "refresh token required.", "code": "missing_refresh"}, status=400)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            pass  # already invalid/expired/blacklisted - logout is idempotent either way
        return Response(status=204)


class MeView(APIView):
    """GET the current user - role, assigned warehouses - for app bootstrap."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
