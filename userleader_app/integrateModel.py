import os
import joblib
import pandas as pd
import numpy as np
import logging
import traceback

# Initialize logger
logger = logging.getLogger(__name__)

def predict_most_frequent_name(wavenumbers, transmittance, model_path=None):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(current_dir, 'models')

        # Set default paths if none provided
        if model_path is None:
            model_path = os.path.join(models_dir, 'best_rf_model.pkl')
        scaler_path = os.path.join(models_dir, 'scaler.pkl')
        label_encoder_path = os.path.join(models_dir, 'label_encoder.pkl')

        # Check all files exist
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not os.path.exists(scaler_path):
            logger.error(f"Scaler file not found: {scaler_path}")
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        if not os.path.exists(label_encoder_path):
            logger.error(f"Label encoder file not found: {label_encoder_path}")
            raise FileNotFoundError(f"Label encoder file not found: {label_encoder_path}")

        # Load model and tools
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        label_encoder = joblib.load(label_encoder_path)

        # Prepare DataFrame
        data_csv = pd.DataFrame({
            'wavenumbers': wavenumbers,
            'transmittance': transmittance
        })

        if not np.isfinite(data_csv.values).all():
            logger.error("Input data contains NaN or infinite values.")
            raise ValueError("Input data contains NaN or infinite values.")

        data_csv = data_csv.astype(float)

        # Normalize %T to [0–1] if needed
        if data_csv['transmittance'].max() > 1.5:
            logger.info("Normalizing %T to [0–1] range.")
            data_csv['transmittance'] = data_csv['transmittance'] / 100.0

        logger.info("Scaling data.")
        scaled_array = scaler.transform(data_csv[['wavenumbers', 'transmittance']])
        scaled_df = pd.DataFrame(scaled_array, columns=['wavenumbers', 'transmittance'])

        scaled_df.rename(columns={
            'wavenumbers': 'Wavenumber',
            'transmittance': 'Transmittance'
        }, inplace=True)

        # Feature Engineering
        scaled_df["gradient_transmittance"] = np.gradient(scaled_df["Transmittance"])
        scaled_df["curvature_transmittance"] = np.gradient(scaled_df["gradient_transmittance"])
        scaled_df["scaled_wavenumbers"] = scaled_df["Wavenumber"]
        scaled_df["scaled_transmittance"] = scaled_df["Transmittance"]

        expected_features = [
            'curvature_transmittance',
            'gradient_transmittance',
            'scaled_transmittance',
            'scaled_wavenumbers'
        ]

        for col in expected_features:
            if col not in scaled_df.columns:
                raise ValueError(f"Missing expected column: {col}")

        X_new_model = scaled_df[expected_features]

        if hasattr(model, "feature_names_in_"):
            X_new_model = X_new_model.reindex(columns=model.feature_names_in_, fill_value=0)

        if len(X_new_model) < 50:
            logger.warning("Input data is very short — prediction may be less accurate.")

        logger.info("Making predictions.")
        y_new_pred = model.predict(X_new_model)

        # Unseen label values
        unseen_labels = set(y_new_pred) - set(range(len(label_encoder.classes_)))
        if unseen_labels:
            raise ValueError(f"Model predicted unseen labels: {unseen_labels}. Retrain model or update LabelEncoder.")

        predicted_names = label_encoder.inverse_transform(y_new_pred)
        most_frequent_name = pd.Series(predicted_names).mode()[0]

        return most_frequent_name

    except Exception as e:
        logger.error(f"An error occurred in predict_most_frequent_name: {e}")
        logger.debug(traceback.format_exc())
        raise


# Testing
def test_predict_most_frequent_name():
    test_wavenumbers = [400, 500, 600, 700, 800, 900, 1000]
    test_transmittance = [0.8, 0.76, 0.9, 0.88, 0.82, 0.85, 0.8]

    try:
        result = predict_most_frequent_name(test_wavenumbers, test_transmittance)
        print("✅ Most frequent predicted name:", result)
    except Exception as e:
        print("❌ Test failed:", e)


if __name__ == '__main__':
    test_predict_most_frequent_name()
