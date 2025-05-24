#!/usr/bin/env python
import os, sys, logging, traceback

# When running this file directly, set __package__ so relative imports work.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "userleader_app"

# Add the project root to the Python path so that "userleader_backend.settings" can be found.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "userleader_backend.settings")
import django
django.setup()

from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from drf_yasg.utils import swagger_auto_schema

import pandas as pd
import numpy as np

from .serializer import (
    CustomUserSerializer,
    MyTokenObtainPairSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    CSVSerializer
)
from .models import CustomUser
from .peak_detection import (
    process_reference_data,
    detect_peaks_and_match,
    group_and_filter_peaks_dynamic,
    generate_report
)
from .integrateModel import predict_most_frequent_name
from .csv_read import csv_read

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
            token = RefreshToken(request.data.get("refresh_token"))
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        old = serializer.validated_data["old_password"]
        new = serializer.validated_data["new_password"]
        if not check_password(old, request.user.password):
            return Response({"message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new)
        request.user.save()
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

class DataHandlingView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes    = (MultiPartParser, FormParser)
    serializer_class  = CSVSerializer

    @swagger_auto_schema(operation_description="Upload file to process both peak detection and model prediction.")
    def post(self, request, *args, **kwargs):
        logger.info("Received request for file handling.")
        try:
            # Validate upload
            if "file" not in request.data:
                return Response({"error": "No file provided. Please upload a CSV file."},
                                status=status.HTTP_400_BAD_REQUEST)

            uploaded = request.data["file"]
            if not uploaded.name.lower().endswith(".csv"):
                return Response({"error": "Invalid file format. Please upload a CSV file."},
                                status=status.HTTP_400_BAD_REQUEST)

            content = uploaded.read().decode("utf-8")
            logger.info(f"File content preview: {content[:100]}")

            # Parse CSV
            file_data = csv_read(content)
            if "wavenumber" not in file_data or not ("absorbance" in file_data or "transmittance" in file_data):
                raise ValueError("Uploaded file must contain 'wavenumber' and 'absorbance' or 'transmittance' columns.")

            wv = file_data["wavenumber"]
            if "absorbance" in file_data:
                ab = file_data["absorbance"]
                tr = (10 ** (-np.array(ab))) * 100
            else:
                tr = file_data["transmittance"]
                ab = -np.log10(np.array(tr) / 100)

            df = pd.DataFrame({"wavenumber": wv, "absorbance": ab, "transmittance": tr})
            df = df.dropna().sort_values("wavenumber").reset_index(drop=True)
            if df.empty:
                raise ValueError("Uploaded file contains no valid data.")

            # Peak detection
            base = os.path.dirname(os.path.abspath(__file__))
            ref_xlsx = os.path.join(base, "data", "IR_Correlation_Table_5000_to_250.xlsx")
            reference_data = process_reference_data(ref_xlsx)
            detected = detect_peaks_and_match(df, reference_data, prominence=0.005)
            grouped  = group_and_filter_peaks_dynamic(detected, "Bond Type", "wavenumber")
            peak_report = generate_report(grouped, report_type=request.data.get("report_type", "absorbance"))

            # Model prediction  
            model_pth = os.path.join(base, "models", "best_rf_model.pkl")
            compound_name = predict_most_frequent_name(
                wavenumbers   = df["wavenumber"].tolist(),
                transmittance = df["transmittance"].tolist(),
                model_path    = model_pth
            )
            logger.info(f"Predicted compound: {compound_name}")

            # Build response
            return Response({
                "compound_name": compound_name,
                "message":       "Prediction completed successfully.",
                "peak_report":   peak_report,
                "data": {
                    "wavenumber":    df["wavenumber"].tolist(),
                    "transmittance": df["transmittance"].tolist(),
                    "absorbance":    df["absorbance"].tolist(),
                }
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Unexpected error")
            return Response({"error": str(e), "traceback": traceback.format_exc()},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
