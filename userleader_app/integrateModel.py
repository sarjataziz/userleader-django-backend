import os
import joblib
import pandas as pd

def explain_prediction(wavelength, transmittance, predicted_name):
    return (f"Detected chemical is {predicted_name} because the wavelength {wavelength} "
            f"and transmittance {transmittance} match known characteristics.")

def predict_most_frequent_name(wavenumbers, transmittance, model_path=None, excel_file_path=None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, 'models')
    data_dir = os.path.join(current_dir, 'data')

    # Set default paths if none provided
    if model_path is None:
        model_path = os.path.join(models_dir, 'best_rf_model.pkl')
    else:
        if not os.path.isabs(model_path):
            # Check if 'models' is already in the path
            if not model_path.startswith('models' + os.sep):
                model_path = os.path.join(models_dir, model_path)
            else:
                model_path = os.path.join(current_dir, model_path)

    scaler_path = os.path.join(models_dir, 'scaler.pkl')
    label_encoder_path = os.path.join(models_dir, 'label_encoder.pkl')

    if excel_file_path is None:
        excel_file_path = os.path.join(data_dir, 'all_in_one.xlsx')
    else:
        if not os.path.isabs(excel_file_path):
            if not excel_file_path.startswith('data' + os.sep):
                excel_file_path = os.path.join(data_dir, excel_file_path)
            else:
                excel_file_path = os.path.join(current_dir, excel_file_path)

    # Check if the model and data files exist
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
    if not os.path.exists(label_encoder_path):
        raise FileNotFoundError(f"Label encoder file not found: {label_encoder_path}")
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

    # Load the model, scaler, and label encoder
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    label_encoder = joblib.load(label_encoder_path)

    # Create a DataFrame from the provided wavenumbers and transmittance
    data_csv = pd.DataFrame({
        'wavenumbers': wavenumbers,
        'transmittance': transmittance
    })

    # Scale the data
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
    y_new_pred = model.predict(X_new_model)

    # Load the Excel file and prepare data for decoding the predictions
    data = pd.read_excel(excel_file_path)
    data.dropna(subset=['Name', 'wavenumbers', 'transmittance'], inplace=True)

    # Fit the label encoder with the correct data
    label_encoder.fit(data['Name'])
    predicted_names = label_encoder.inverse_transform(y_new_pred)

    # Determine the most frequently predicted name
    most_frequent_name = pd.Series(predicted_names).mode()[0]

    # Find an example occurrence for explanation
    index = next(i for i, name in enumerate(predicted_names) if name == most_frequent_name)
    wavelength = wavenumbers[index]
    transmittance_value = transmittance[index]

    # Generate the explanation
    explanation = explain_prediction(wavelength, transmittance_value, most_frequent_name)

    return most_frequent_name, explanation
