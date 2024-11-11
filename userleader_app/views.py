from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializer import *
from .models import *
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
import csv
from drf_yasg.utils import swagger_auto_schema
from .csv_read import csv_read
from rest_framework_simplejwt.tokens import RefreshToken
from .peak_detection import process_reference_data, detect_peaks_and_match, generate_report
import os

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
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


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

            # Read the file content
            file_content = uploaded_file.read().decode('utf-8')

            # Use csv_read.py to extract data
            data = csv_read(file_content)

            # Ensure necessary data is present
            if 'wavenumber' not in data or 'transmittance' not in data:
                raise Exception("Uploaded file must contain 'wavenumber' and 'transmittance' data.")

            # Process reference data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            reference_path = os.path.join(current_dir, 'data', 'Table-1.xlsx')
            reference_data = process_reference_data(reference_path)

            # Detect peaks and match functional groups
            detected_peaks_df = detect_peaks_and_match(
                data['wavenumber'],
                data['transmittance'],
                reference_data
            )

            # Generate the report
            report = generate_report(detected_peaks_df)

            # Return the result as a response
            return Response({
                'report': report,
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
