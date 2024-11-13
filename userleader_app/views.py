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
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from drf_yasg.utils import swagger_auto_schema
from .csv_read import csv_read
from .peak_detection import process_reference_data, detect_peaks_and_match, generate_report
from .integrateModel import predict_most_frequent_name
import os
import logging
import traceback

# Initialize logger
logger = logging.getLogger(__name__)

# Ensure the logger is configured to output messages
logging.basicConfig(level=logging.INFO)

from django.http import HttpResponse

def homepage(request):
    return HttpResponse("Welcome to UserLeader Backend")

class CustomUserCreateView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (AllowAny,)

class SigninView(TokenObtainPairView):
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
            logger.error(f"Logout error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')

            if not check_password(old_password, request.user.password):
                return Response({"message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

            request.user.set_password(new_password)
            request.user.save()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DataHandlingView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CSVSerializer

    @swagger_auto_schema(operation_description='Upload file to process both peak detection and model prediction.')
    def post(self, request, *args, **kwargs):
        logger.info("Received request for file handling.")

        try:
            # File validation
            if 'file' not in request.data:
                logger.warning('No file provided in the request.')
                return Response({'error': 'No file provided. Please upload a CSV file.'}, status=status.HTTP_400_BAD_REQUEST)

            uploaded_file = request.data['file']
            file_extension = uploaded_file.name.split('.')[-1]
            if file_extension.lower() != 'csv':
                logger.warning('Invalid file format uploaded.')
                return Response({'error': 'Invalid file format. Please upload a CSV file.'}, status=status.HTTP_400_BAD_REQUEST)

            logger.info("File uploaded successfully.")

            # Read CSV content
            try:
                file_content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError as ude:
                logger.error(f"Unicode decode error: {ude}")
                return Response({'error': 'File encoding not supported. Please upload a UTF-8 encoded file.'}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"File content preview: {file_content[:100]}")  # Log first 100 characters

            data = csv_read(file_content)
            logger.info(f"CSV data processed successfully: {data}")

            # Ensure necessary data is present
            if 'wavenumber' not in data or 'transmittance' not in data:
                logger.error("CSV file missing 'wavenumber' or 'transmittance' data.")
                raise ValueError("Uploaded file must contain 'wavenumber' and 'transmittance' data.")

            logger.info("Required data fields found in CSV.")

            # Convert data to float
            try:
                data['wavenumber'] = [float(x) for x in data['wavenumber']]
                data['transmittance'] = [float(x) for x in data['transmittance']]
            except ValueError as ve:
                logger.error(f"Data conversion error: {ve}")
                return Response({'error': 'Data contains non-numeric values.'}, status=status.HTTP_400_BAD_REQUEST)

            # Path setup for model and reference data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, 'models', 'best_rf_model.pkl')
            reference_path = os.path.join(current_dir, 'data', 'Table-1.xlsx')

            # Check if model and data files exist
            if not os.path.exists(model_path):
                logger.error(f"Model file not found at: {model_path}")
                return Response({'error': 'Model file not found. Please check the model path.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if not os.path.exists(reference_path):
                logger.error(f"Reference file not found at: {reference_path}")
                return Response({'error': 'Reference file not found. Please check the path.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info("Model and reference files verified.")

            # Peak detection and functional group matching
            logger.info("Processing reference data for peak detection.")
            reference_data = process_reference_data(reference_path)
            logger.info("Reference data processed successfully.")

            detected_peaks_df = detect_peaks_and_match(data['wavenumber'], data['transmittance'], reference_data)
            peak_report = generate_report(detected_peaks_df)
            logger.info("Peak detection completed.")

            # Model prediction
            logger.info("Running model prediction.")
            try:
                compound_name = predict_most_frequent_name(
                    data["wavenumber"],
                    data["transmittance"],
                    model_path=model_path
                )
                logger.info(f"Model prediction completed successfully. Predicted compound name: {compound_name}")
            except Exception as e:
                logger.error(f"Error during compound prediction: {e}")
                logger.debug(traceback.format_exc())
                return Response({'error': 'Error during compound prediction.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Optimizing and formatting the response
            response_data = {
                "compound_name": compound_name,
                "peak_report": peak_report,
                "data": {
                    "wavenumber": data["wavenumber"],
                    "transmittance": data["transmittance"],
                    "wavelengths": data.get("wavelengths", []),
                    "absorbance": data.get("absorbance", [])
                }
            }

            logger.info("File processed successfully.")
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.error(f"ValueError encountered: {ve}")
            logger.debug(traceback.format_exc())
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("An unexpected error occurred.")
            return Response({'error': f'Internal server error. Details: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
