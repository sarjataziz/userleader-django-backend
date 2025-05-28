#!/usr/bin/env python
import os, sys, logging, traceback
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

# Setup Django path if running standalone
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "userleader_app"
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "userleader_backend.settings")
import django; django.setup()

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
            return Response({"message":"Old password is incorrect."},status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new); request.user.save()
        return Response({"message":"Password changed successfully."},status=status.HTTP_200_OK)

class DataHandlingView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CSVSerializer

    @swagger_auto_schema(operation_description="Upload file to process both peak detection and model prediction.")
    def post(self, request, *args, **kwargs):
        logger.info("Starting file handling request...")

        try:
            if "file" not in request.data:
                logger.warning("No file key found in request.")
                return Response({"error": "No file provided. Please upload a CSV file."},
                                status=status.HTTP_400_BAD_REQUEST)

            uploaded = request.data["file"]
            filename = uploaded.name
            if not filename.lower().endswith(".csv"):
                logger.warning(f"Invalid file format: {filename}")
                return Response({"error": "Invalid file format. Please upload a CSV file."},
                                status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Received file: {filename}")
            content = uploaded.read().decode("utf-8", errors="replace")
            logger.debug(f"File content preview:\n{content[:100]}")

            # Read CSV content
            try:
                file_data = csv_read(content)
            except Exception as e:
                logger.error(f"Error reading CSV in `csv_read()`: {e}")
                raise ValueError("Failed to read CSV content. Please check your file formatting.")

            if "wavenumber" not in file_data or not ("absorbance" in file_data or "transmittance" in file_data):
                raise ValueError("CSV must contain 'wavenumber' and either 'absorbance' or 'transmittance' columns.")

            # Convert raw values
            try:
                wv = file_data["wavenumber"]
                if "absorbance" in file_data:
                    ab = np.array(file_data["absorbance"], dtype=float)
                    tr = 10 ** (-ab)
                else:
                    tr_raw = np.array(file_data["transmittance"], dtype=float)
                    tr = np.where(tr_raw > 1, tr_raw / 100.0, tr_raw)
                    ab = -np.log10(np.clip(tr, 1e-8, 1.0))
            except Exception as e:
                logger.error(f"Error processing numerical columns: {e}")
                raise ValueError("Failed to process absorbance/transmittance data. Check for invalid numeric values.")

            # Create cleaned DataFrame
            df = pd.DataFrame({
                "wavenumber":    wv,
                "transmittance": tr,
                "absorbance":    ab
            }).dropna().sort_values("wavenumber").reset_index(drop=True)

            if df.empty:
                raise ValueError("Processed DataFrame is empty after cleaning.")

            # Peak detection
            try:
                base = os.path.dirname(os.path.abspath(__file__))
                ref_xlsx = os.path.join(base, "data", "IR_Correlation_Table_5000_to_250.xlsx")
                reference_data = process_reference_data(ref_xlsx)
                detected = detect_peaks_and_match(df, reference_data, prominence=0.005)
                grouped = group_and_filter_peaks_dynamic(detected, "Bond Type", "wavenumber")
                peak_report = generate_report(grouped, report_type=request.data.get("report_type", "absorbance"))
            except Exception as e:
                logger.error(f"Peak detection failed: {e}")
                raise ValueError("Peak detection or correlation table processing failed.")

            # Prediction
            try:
                model_pth = os.path.join(base, "models", "best_rf_model.pkl")
                compound_name = predict_most_frequent_name(
                    wavenumbers=df["wavenumber"].tolist(),
                    transmittance=df["transmittance"].tolist(),
                    model_path=model_pth
                )
                logger.info(f"Predicted compound: {compound_name}")
            except Exception as e:
                logger.error(f"Model prediction failed: {e}")
                raise ValueError("Model prediction failed. Ensure the model file exists and is valid.")

            # Response
            return Response({
                "compound_name": compound_name,
                "message": "Prediction completed successfully.",
                "peak_report": peak_report,
                "data": {
                    "wavenumber":    df["wavenumber"].tolist(),
                    "transmittance": (df["transmittance"] * 100).round(4).tolist(), 
                    "absorbance":    df["absorbance"].round(6).tolist()
                }
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.warning(f"ValueError in file handling: {ve}")
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            tb = traceback.format_exc()
            logger.critical(f"Unhandled error during file processing: {e}")
            logger.debug(tb)
            return Response({
                "error": str(e),
                "traceback": tb
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
