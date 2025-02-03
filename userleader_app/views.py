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
from .peak_detection import (
    process_reference_data,
    calculate_transmittance,
    calculate_absorbance,
    detect_peaks_and_match,
    group_and_filter_peaks_dynamic,
    generate_report
)
from .integrateModel import predict_most_frequent_name
import os
import logging
import traceback
import pandas as pd
from io import StringIO
import numpy as np
from .csv_read import csv_read 

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CustomUser views
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

            # Read CSV using custom csv_read function
            try:
                file_data = csv_read(file_content)
                logger.debug(f"CSV data keys: {file_data.keys()}")

                # Check for required data
                if 'wavenumber' not in file_data or ('absorbance' not in file_data and 'transmittance' not in file_data):
                    raise ValueError("Uploaded file must contain 'wavenumber' and 'absorbance' or 'transmittance' columns.")

                # Ensure data arrays have the same length and collect valid indices
                wavenumber = file_data['wavenumber']
                logger.debug(f"wavenumber type: {type(wavenumber)}, length: {len(wavenumber)}")

                if 'absorbance' in file_data:
                    absorbance = file_data['absorbance']
                    logger.debug(f"absorbance type: {type(absorbance)}, length: {len(absorbance)}")
                    if len(wavenumber) != len(absorbance):
                        raise ValueError("Data columns have mismatched lengths.")
                    transmittance = (10 ** (-np.array(absorbance))) * 100
                else:
                    transmittance = file_data['transmittance']
                    logger.debug(f"transmittance type: {type(transmittance)}, length: {len(transmittance)}")
                    if len(wavenumber) != len(transmittance):
                        raise ValueError("Data columns have mismatched lengths.")
                    # Convert transmittance to absorbance
                    transmittance_array = np.array(transmittance)
                    absorbance = -np.log10(transmittance_array / 100)

                data_df = pd.DataFrame({
                    'wavenumber': wavenumber,
                    'absorbance': absorbance,
                    'transmittance': transmittance
                })

                data_df['wavenumber'] = pd.to_numeric(data_df['wavenumber'], errors='coerce')
                data_df['absorbance'] = pd.to_numeric(data_df['absorbance'], errors='coerce')
                data_df['transmittance'] = pd.to_numeric(data_df['transmittance'], errors='coerce')

                data_df.dropna(subset=['wavenumber', 'absorbance', 'transmittance'], inplace=True)
                data_df.sort_values(by='wavenumber', inplace=True)

                logger.info("CSV data processed successfully.")

            except Exception as e:
                logger.error(f"Error processing CSV file: {e}")
                return Response({'error': f'Error processing CSV file: {e}'}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure necessary data is present
            if data_df.empty:
                logger.error("CSV file contains no valid data.")
                return Response({'error': "Uploaded file contains no valid data."}, status=status.HTTP_400_BAD_REQUEST)

            # Path setup for model and reference data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, 'models', 'best_rf_model.pkl')
            # Corrected reference file name
            reference_path = os.path.join(current_dir, 'data', 'IR_Correlation_Table_5000_to_250.xlsx')

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

            # Detect peaks and match
            detected_peaks = detect_peaks_and_match(data_df, reference_data, prominence=0.005)
            logger.info(f"Detected peaks:\n{detected_peaks}")

            # Group and filter peaks
            grouped_peaks = group_and_filter_peaks_dynamic(detected_peaks, group_by='Bond Type', sort_by='wavenumber')

            if grouped_peaks.empty:
                logger.warning("No peaks were detected or matched to the reference data.")
                peak_report = ["No peaks were detected or matched to the reference data."]
            else:
                # Get the user's choice for report type (Absorbance or Transmittance)
                report_type = request.data.get('report_type', 'absorbance').lower()
                if report_type not in ['absorbance', 'transmittance']:
                    report_type = 'absorbance'
                peak_report = generate_report(grouped_peaks, report_type=report_type)
                logger.info("Peak detection completed successfully.")

            # Model prediction
            logger.info("Running model prediction.")
            try:
                compound_name = predict_most_frequent_name(
                    data_df["wavenumber"].tolist(),
                    data_df["absorbance"].tolist(),
                    model_path=model_path
                )
                logger.info(f"Model prediction completed successfully. Predicted compound name: {compound_name}")
            except Exception as e:
                logger.error(f"Error during compound prediction: {e}")
                logger.debug(traceback.format_exc())
                return Response({'error': 'Error during compound prediction.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # New logic: Check if the predicted compound exists in the reference dataset
            try:
                reference_df = pd.read_excel(reference_path)
                reference_compounds = set(reference_df['Name'].dropna().str.lower())
                if compound_name.lower() not in reference_compounds:
                    compound_name = "Compound name isn't in the model database."
            except Exception as e:
                logger.error(f"Error processing reference dataset for compound check: {e}")
                compound_name = "Compound name isn't in the model database."

            # Prepare the response
            response_data = {
                "compound_name": compound_name,
                "peak_report": peak_report,
                "data": {
                    "wavenumber": data_df["wavenumber"].tolist(),
                    "transmittance": data_df["transmittance"].tolist(),
                    "absorbance": data_df["absorbance"].tolist()
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
            return Response({
                'error': f'Internal server error. Details: {str(e)}',
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
