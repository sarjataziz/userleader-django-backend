## README: IR Spectrum Peak Detection and Functional Group Analysis

### Overview

This project is designed to detect peaks in an IR spectrum, correlate detected peaks with a reference spectrum, and predict the most probable compound name using a machine learning model. The system processes user-uploaded spectral data, detects peaks, matches functional groups from a reference dataset, and generates a detailed report.

### Project Structure

```
userleader_backend/
├── userleader_app/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── csv_read.py
│   ├── integrateModel.py
│   ├── peak_detection.py
│   ├── views.py
│   ├── data/
│   │   ├── IR_Correlation_Table_5000_to_250.xlsx
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
├── userleader_backend/
├── requirements.txt
├── manage.py
├── utils/
├── templates/
```

### Features

1. **CSV File Parsing**:
   - Reads user-uploaded ``` CSV, ASP, JDX, SPE, SAP ``` files containing IR spectral data.
   - Supports both absorbance and transmittance data formats.
   - Ensures consistent data formatting by handling errors in input, including:
     - Detecting missing or mismatched column headers.
     - Validating and cleaning numerical data by removing non-numeric characters and handling edge cases (e.g., empty or incomplete rows).
     - Converting all data to a uniform numerical format to ensure compatibility with downstream processing.
     - Dynamically parsing mixed headers and inferring data relationships even when unconventional headers are used.

2. **Peak Detection**:
   - Uses the **Savitzky-Golay** filter to smooth absorbance data.
   - Detects peaks using the `find_peaks` function from `scipy.signal`.

3. **Reference Spectrum Matching**:
   - Matches detected peaks with reference functional groups in a reference dataset (Excel file).
   - Implements a dynamic grouping and filtering mechanism to extract relevant peaks.

4. **Machine Learning Prediction**:
   - Utilizes a pre-trained Random Forest model to predict the compound name based on the spectrum.
   - Scales data and ensures compatibility with the model.

5. **Report Generation**:
   - Provides a detailed summary of detected peaks, functional groups, and predicted compound names.
   - Allows users to choose between absorbance or transmittance-based reporting.

### Workflow

1. **Data Upload**:
   - Users upload an IR spectrum ``` CSV, ASP, JDX, SPE, SAP ``` file via an API.
   - The file must contain wavenumber and either absorbance or transmittance data.

2. **Data Preprocessing**:
   - The `csv_read.py` script extracts and validates wavenumber and absorbance/transmittance columns.
   - Converts transmittance to absorbance (if needed) using the formula:

     \[ Absorbance = -log10(Transmittance / 100) \] <br> or <br>
      [ Transmittance = 10^(-A) / 100 ]

3. **Reference Data Processing**:
   - Reads functional group information from `IR_Correlation_Table_5000_to_250.xlsx`.
   - Parses wavenumber ranges and calculates tolerances for matching.

4. **Peak Detection**:
   - Smooths the absorbance data using the Savitzky-Golay filter.
   - Detects peaks based on prominence and wavenumber alignment.

5. **Functional Group Matching**:
   - Matches detected peaks to the closest functional group in the reference spectrum.
   - Provides exact or approximate matches based on the defined bounds.

6. **Prediction**:
   - Uses a Random Forest model to predict the compound name.
   - Maps wavenumber and transmittance data to model input features.

7. **Report Generation**:
   - Summarizes detected peaks, matched functional groups, and the predicted compound name.

### Formulas Used

1. **Transmittance to Absorbance Conversion**:<br>
   \[ A = -log_{10}(Transmittance / 100) \]

2. **Absorbance to Transmittance Conversion**:<br>
   \[ Transmittance = 10^(-A) / 100 \]

3. **Peak Center Calculation**:
   - For ranges: 
     \[ Center = (Low + High) / 2 \]
   - For uncertainty: 
     \[ Low = Center - Uncertainty, 
      High = Center + Uncertainty \]

### Exact Correlation Between Model and Reference Spectrum

1. **Reference Spectrum Role**:
   - Acts as a knowledge base for matching detected peaks to known functional groups.
   - Provides wavenumber ranges, bond types, and functional group associations.

2. **Model Role**:
   - Predicts the compound based on detected peak features.
   - Relies on patterns in wavenumber and transmittance/absorbance.

3. **Interdependence**:
   - Changing the reference spectrum affects peak detection and functional group matching.
   - Example: Removing a functional group (e.g., hydroxyl) from the reference spectrum could lead to incorrect model predictions for compounds containing that group.

### Steps to Update Reference Spectrum

1. Update `IR_Correlation_Table_5000_to_250.xlsx` with new wavenumber ranges, bond types, and functional groups.
2. Ensure correct formatting:
   - Columns: `Wavenumbers (cm-1)`, `Bond Type`, `Functional Group`, `Compound`.
3. Restart the application to use the updated reference data.

### Limitations

1. **Data Quality**:
   - Poor-quality spectra, such as those with high levels of noise, missing wavenumber ranges, or inconsistent absorbance/transmittance values, can significantly reduce accuracy.
     - Example: A spectrum with significant baseline drift or excessive noise may cause incorrect peak detection or missed peaks altogether, resulting in flawed predictions.

2. **Reference Spectrum Coverage**:
   - The system heavily depends on the completeness and accuracy of the reference spectrum for functional group matching.
     - Example: If the reference spectrum lacks key functional groups or contains outdated wavenumber ranges, it may lead to mismatches or false negatives in the detection process.

3. **Model Generalization**:
   - The pre-trained model is optimized for specific training data and may fail to generalize well to compounds or spectra outside its training set.
     - Example: A novel compound with unique spectral features not represented in the training data could result in an inaccurate or uncertain prediction.

4. **Complex Mixtures**:
   - This system is primarily designed for analyzing single-compound spectra and may face challenges when dealing with overlapping peaks in mixtures.
     - Example: A spectrum containing two compounds with overlapping wavenumber ranges may lead to ambiguous peak assignments, reducing prediction accuracy.

### Dependencies

- Python 3.9+
- Django 3.4+
- pandas
- numpy
- scipy
- matplotlib
- scikit-learn
- joblib
- django-rest-framework

### API Endpoints

#### 1. **File Upload**

- Endpoint: `/api/upload/`
- Method: `POST`
- Description: Upload a CSV file for peak detection and compound prediction.
- Response:
  ```json
  {
      "compound_name": "Predicted Compound Name",
      "peak_report": [
          "Detailed peak match report"
      ],
      "data": {
          "wavenumber": [...],
          "absorbance": [...],
          "transmittance": [...]
      }
  }
  ```

### Conclusion

This system seamlessly integrates reference-based peak matching with machine learning predictions to provide a comprehensive analysis of IR spectra. Future enhancements could include:

- Supporting additional spectral data formats.
- Real-time visualization of spectra and peaks.
- Improving model accuracy by incorporating updated reference datasets and advanced machine learning techniques.

