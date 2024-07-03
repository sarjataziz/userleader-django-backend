import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder


def predict_most_frequent_name(wavenumbers, transmittance, model_path=r'userleader_app\random_forest_model.pkl', excel_file_path=r'userleader_app\all_in_one.xlsx'):
    # Create a DataFrame from the provided wavenumbers and transmittance
    data_csv = pd.DataFrame({'Wavenumber': wavenumbers, 'Transmittance': transmittance})

    # Ensure the column names are consistent and scale the data
    scaler = StandardScaler()
    data_csv[['Wavenumber', 'Transmittance']] = scaler.fit_transform(data_csv[['Wavenumber', 'Transmittance']])

    # Load the model using joblib.load
    model = joblib.load(model_path)

    # Making predictions with the loaded model
    y_new_pred = model.predict(data_csv[['Wavenumber', 'Transmittance']])

    # Decode the predicted names using LabelEncoder
    data = pd.read_excel(excel_file_path)
    data = data.dropna(subset=['Name', 'wavenumbers', 'transmittance'])

    label_encoder = LabelEncoder()
    data['name_encoded'] = label_encoder.fit_transform(data['Name'])
    predicted_names = label_encoder.inverse_transform(y_new_pred)

    # Determine the most frequently predicted name
    most_frequent_name = pd.Series(predicted_names).mode()[0]

    return most_frequent_name

