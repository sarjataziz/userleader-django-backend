from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializer import (
    CustomUserSerializer,
    MyTokenObtainPairSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    CSVSerializer
)
from .models import CustomUser
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from drf_yasg.utils import swagger_auto_schema
from .csv_read import csv_read
from .integrateModel import predict_most_frequent_name
from django.http import HttpResponse
import os

# Add the index view function here
def index(request):
    return HttpResponse("Welcome to UserLeader App!")

# Your existing views
class CustomUserCreateView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (AllowAny,)

class SigninView(TokenObtainPairView):
    # Replace the serializer with your custom
    serializer_class = MyTokenObtainPairSerializer

class LogoutView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer

    def create(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')

            # Check if the old password matches the current password
            if not check_password(old_password, request.user.password):
                return Response({"message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

            # Change the password and save the user object
            request.user.set_password(new_password)
            request.user.save()

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DataHandlingView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CSVSerializer

    @swagger_auto_schema(operation_description='Upload file...')
    def post(self, request, *args, **kwargs):
        try:
            uploaded_file = request.data['file']
            file_extension = uploaded_file.name.split('.')[-1]
            if file_extension.lower() != 'csv':
                raise Exception("Invalid file format. Please upload a CSV file.")

            # Get the file content from the uploaded file object
            file_content = uploaded_file.read().decode('utf-8')

            # Pass the file content to csv_read function
            data = csv_read(file_content)

            # Ensure that the model and data file paths are correctly passed to the prediction function
            model_path = os.path.join('userleader_app', 'models', 'best_rf_model.pkl')
            excel_file_path = os.path.join('userleader_app', 'data', 'all_in_one.xlsx')

            # Get the most frequent predicted compound name and the explanation
            compound_name, explanation = predict_most_frequent_name(
                data["wavenumber"],
                data["transmittance"],
                model_path=model_path,
                excel_file_path=excel_file_path
            )

            # Return the result as a response
            return Response({
                'compound_name': compound_name,
                'explanation': explanation,
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

