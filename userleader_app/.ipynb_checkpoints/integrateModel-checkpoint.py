import os
import joblib
import pandas as pd

def explain_prediction(wavelength, transmittance, predicted_name):
    return (f"Detected chemical is {predicted_name} because the wavelength {wavelength} "
            f"and transmittance {transmittance} match known characteristics.")

def predict_most_frequent_name(wavenumbers, transmittance, model_path=None, excel_file_path=None):
    # Get the current working directory to form absolute paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set default paths if none provided
    if model_path is None:
        model_path = os.path.join(current_dir, 'best_rf_model.pkl')  # Model is directly in the main folder
    if excel_file_path is None:
        excel_file_path = os.path.join(current_dir, 'all_in_one.xlsx')  # Excel file is directly in the main folder

    # Check if the model and excel file exist
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
    
    print(f"Loading model from: {model_path}")
    print(f"Loading Excel data from: {excel_file_path}")

    # Create a DataFrame from the provided wavenumbers and transmittance
    data_csv = pd.DataFrame({'Wavenumber': wavenumbers, 'Transmittance': transmittance})

    # Load the model, scaler, and label encoder
    scaler_path = os.path.join(current_dir, 'scaler.pkl')  # Scaler is directly in the main folder
    label_encoder_path = os.path.join(current_dir, 'label_encoder.pkl')  # Label encoder is directly in the main folder

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    label_encoder = joblib.load(label_encoder_path)

    # Ensure the column names are consistent and scale the data
    data_csv[['Wavenumber', 'Transmittance']] = scaler.transform(data_csv[['Wavenumber', 'Transmittance']])

    # Making predictions with the loaded model
    y_new_pred = model.predict(data_csv[['Wavenumber', 'Transmittance']])

    # Load the Excel file and prepare data for decoding the predictions
    data = pd.read_excel(excel_file_path)
    data = data.dropna(subset=['Name', 'wavenumbers', 'transmittance'])

    # Fit the label encoder with the correct data
    label_encoder.fit_transform(data['Name'])
    predicted_names = label_encoder.inverse_transform(y_new_pred)

    # Determine the most frequently predicted name
    most_frequent_name = pd.Series(predicted_names).mode()[0]

    # Find an example occurrence of the most frequent predicted name
    most_freq_indices = [i for i, name in enumerate(predicted_names) if name == most_frequent_name]
    index = most_freq_indices[0]

    # Extract the corresponding wavelength and transmittance values
    wavelength = wavenumbers[index]
    transmittance_value = transmittance[index]

    # Generate the explanation for the most frequently predicted chemical
    explanation = explain_prediction(wavelength, transmittance_value, most_frequent_name)

    return most_frequent_name, explanation


import os

# Get the absolute path to the models folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(BASE_DIR, 'userleader_app', 'best_rf_model.pkl')

# Check if the model file exists
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found: {model_path}")

# Then proceed with loading the model using the absolute path
model = joblib.load(model_path)

print(f"Model file path: {model_path}")
