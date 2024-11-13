from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)
from .views import (
    CustomUserCreateView,
    SigninView,
    LogoutView,
    ChangePasswordView,
    DataHandlingView
)

urlpatterns = [
    path('api/v1/signup/', CustomUserCreateView.as_view(), name='signup'),
    path('api/v1/signin/', SigninView.as_view(), name='signin'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/v1/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/v1/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/v1/file-handling/', DataHandlingView.as_view(), name='file_handling'),
]
