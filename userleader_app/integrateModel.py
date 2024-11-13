import os
import joblib
import pandas as pd
import numpy as np
import logging
import traceback

# Initialize logger
logger = logging.getLogger(__name__)

def predict_most_frequent_name(wavenumbers, transmittance, model_path=None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, 'models')

    # Set default paths if none provided
    if model_path is None:
        model_path = os.path.join(models_dir, 'best_rf_model.pkl')
    scaler_path = os.path.join(models_dir, 'scaler.pkl')
    label_encoder_path = os.path.join(models_dir, 'label_encoder.pkl')

    try:
        # Check for model files
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not os.path.exists(scaler_path):
            logger.error(f"Scaler file not found: {scaler_path}")
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        if not os.path.exists(label_encoder_path):
            logger.error(f"Label encoder file not found: {label_encoder_path}")
            raise FileNotFoundError(f"Label encoder file not found: {label_encoder_path}")

        # Load the model, scaler, and label encoder
        logger.info("Loading model, scaler, and label encoder.")
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        label_encoder = joblib.load(label_encoder_path)

        # Create a DataFrame from the provided wavenumbers and transmittance
        data_csv = pd.DataFrame({
            'wavenumbers': wavenumbers,
            'transmittance': transmittance
        })

        # Validate data
        if not np.isfinite(data_csv.values).all():
            logger.error("Input data contains NaN or infinite values.")
            raise ValueError("Input data contains NaN or infinite values.")

        # Ensure data types are correct
        data_csv = data_csv.astype(float)

        # Scale the data
        logger.info("Scaling data.")
        data_scaled_array = scaler.transform(data_csv[['wavenumbers', 'transmittance']])
        data_scaled = pd.DataFrame(data_scaled_array, columns=['wavenumbers', 'transmittance'])

        # Rename columns to match the model's expected feature names
        data_scaled.rename(columns={
            'wavenumbers': 'Wavenumber',
            'transmittance': 'Transmittance'
        }, inplace=True)

        # Prepare data for prediction
        X_new_model = data_scaled[['Wavenumber', 'Transmittance']]

        # Make predictions
        logger.info("Making predictions.")
        y_new_pred = model.predict(X_new_model)

        # Use the loaded label encoder to inverse transform the predictions
        predicted_names = label_encoder.inverse_transform(y_new_pred)

        # Determine the most frequently predicted name
        most_frequent_name = pd.Series(predicted_names).mode()[0]

        return most_frequent_name

    except Exception as e:
        logger.error(f"An error occurred in predict_most_frequent_name: {e}")
        logger.debug(traceback.format_exc())
        raise

def test_predict_most_frequent_name():
    # Sample data for testing
    wavenumbers = [400, 500, 600, 700, 800, 900, 1000]
    transmittance = [0.8, 0.76, 0.9, 0.88, 0.82, 0.85, 0.8]

    try:
        # Test the function with sample data
        most_frequent_name = predict_most_frequent_name(wavenumbers, transmittance)
        print("Most frequent predicted name:", most_frequent_name)
    except Exception as e:
        print("Test failed:", e)

if __name__ == '__main__':
    test_predict_most_frequent_name()
