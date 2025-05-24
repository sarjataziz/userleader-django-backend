import os
import joblib
import pandas as pd
import numpy as np
import logging
import traceback

# Initialize logger
logger = logging.getLogger(__name__)

def predict_most_frequent_name(wavenumbers, absorbance=None, transmittance=None, model_path=None):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(current_dir, 'models')

        # Paths
        if model_path is None:
            model_path = os.path.join(models_dir, 'best_rf_model.pkl')
        scaler_path = os.path.join(models_dir, 'scaler.pkl')
        label_encoder_path = os.path.join(models_dir, 'label_encoder.pkl')

        # Load model and transformers
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        label_encoder = joblib.load(label_encoder_path)

        # Validate input
        wavenumbers = np.array(wavenumbers, dtype=float)
        if absorbance is None and transmittance is None:
            raise ValueError("Either absorbance or transmittance must be provided.")

        # Convert if needed
        if absorbance is None:
            transmittance = np.array(transmittance, dtype=float)
            transmittance = np.clip(transmittance, 1e-5, 100.0)
            absorbance = -np.log10(transmittance / 100)
        elif transmittance is None:
            absorbance = np.array(absorbance, dtype=float)
            transmittance = 10 ** (-absorbance) * 100
        else:
            absorbance = np.array(absorbance, dtype=float)
            transmittance = np.array(transmittance, dtype=float)

        # Create DataFrame
        df = pd.DataFrame({
            'wavenumbers': wavenumbers,
            'absorbance': absorbance,
            'transmittance': transmittance
        })

        if not np.isfinite(df.values).all():
            raise ValueError("Input contains NaN or infinite values.")

        # Scale input
        scaled_array = scaler.transform(df[['wavenumbers', 'transmittance']])
        scaled_df = pd.DataFrame(scaled_array, columns=['wavenumbers', 'transmittance'])
        scaled_df.rename(columns={
            'wavenumbers': 'Wavenumber',
            'transmittance': 'Transmittance'
        }, inplace=True)

        # Feature engineering
        scaled_df["gradient_transmittance"] = np.gradient(scaled_df["Transmittance"])
        scaled_df["curvature_transmittance"] = np.gradient(scaled_df["gradient_transmittance"])
        scaled_df["scaled_wavenumbers"] = scaled_df["Wavenumber"]
        scaled_df["scaled_transmittance"] = scaled_df["Transmittance"]

        expected_features = ['curvature_transmittance', 'gradient_transmittance',
                            'scaled_transmittance', 'scaled_wavenumbers']
        X = scaled_df[expected_features]

        # Align with model features
        if hasattr(model, "feature_names_in_"):
            X = X.reindex(columns=model.feature_names_in_, fill_value=0)

        if len(X) < 50:
            logger.warning("Input data is very short — prediction may be less accurate.")

        # Predict
        preds = model.predict(X)

        # Check for unseen class IDs
        unseen = set(preds) - set(range(len(label_encoder.classes_)))
        if unseen:
            raise ValueError(f"Model predicted unseen labels: {unseen}. Please retrain with full label set.")

        decoded = label_encoder.inverse_transform(preds)
        most_frequent = pd.Series(decoded).mode()[0]

        return most_frequent

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Prediction failed: {str(e)}")

def test_predict_most_frequent_name():
    wavenumbers = [400, 500, 600, 700, 800, 900, 1000]
    transmittance = [0.8, 0.76, 0.9, 0.88, 0.82, 0.85, 0.8]

    try:
        result = predict_most_frequent_name(wavenumbers=wavenumbers, transmittance=transmittance)
        print("Most frequent predicted name:", result)
    except Exception as e:
        print("Test failed:", e)

if __name__ == '__main__':
    test_predict_most_frequent_name()
