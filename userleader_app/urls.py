from django.urls import path, include
from rest_framework_simplejwt.views import (
<<<<<<< HEAD
=======
    TokenObtainPairView,
>>>>>>> master
    TokenRefreshView,
    TokenVerifyView
)
from .views import *

urlpatterns = [
<<<<<<< HEAD
    path('signup/', CustomUserCreateView.as_view(), name='signup'),
    path('signin/', SigninView.as_view(), name='signin'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('file-handling/', DataHandlingView.as_view(), name='file_handling'),
=======
    path('api/v1/signup/', CustomUserCreateView.as_view(), name='signup'),
    path('api/v1/signin/', SigninView.as_view(), name='signin'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/v1/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/v1/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/v1/file-handling/', DataHandlingView.as_view()),

>>>>>>> master
]
