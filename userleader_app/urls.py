from django.urls import path, include
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    path('api/v1/signup/', views.CustomUserCreateView.as_view(), name='signup'),
    path('api/v1/signin/', views.SigninView.as_view(), name='signin'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/logout/', views.LogoutView.as_view(), name='auth_logout'),
    path('api/v1/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('api/v1/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/v1/file-handling/', views.DataHandlingView.as_view(), name='file_handling'),
    path('', views.index, name='index'),
]