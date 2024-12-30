# Userleader App (Backend): IR Spectrum Peak Detection and Functional Group Analysis

## Overview

This project is designed to detect peaks in an IR spectrum, correlate detected peaks with a reference spectrum, and predict the most probable compound name using a machine learning model. The system processes user-uploaded spectral data, detects peaks, matches functional groups from a reference dataset, and generates a detailed report.

---

## Key Features

1. **Dynamic Data Handling**:
   - Accepts CSV files containing either `absorbance` or `transmittance` data.
   - Automatically converts between absorbance and transmittance as needed.

2. **Peak Detection**:
   - Detects significant peaks in the spectroscopic data using a smoothed signal.
   - Matches detected peaks to a reference spectrum with both exact and approximate matches.

3. **Compound Prediction**:
   - Uses a trained machine learning model to predict the compound based on detected peaks and matched functional groups.

4. **Dynamic Reference Integration**:
   - Allows updates to the reference spectrum to reflect new or corrected data.
   - Dynamically adjusts detected peaks and predictions based on reference changes.

5. **Comprehensive Reporting**:
   - Provides detailed reports categorizing detected peaks by bond type, functional groups, and associated compounds.
   - Highlights exact and approximate matches to the reference spectrum.

---

## Installation

### Prerequisites
- Python 3.10+
- Django 3.4+
- Required Python packages (listed in `requirements.txt`)

### Steps
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Apply migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the server:
   ```bash
   python manage.py runserver
   ```

---

## Usage

### Frontend Integration
The frontend accepts uploaded CSV files and displays the resulting plots (Absorbance vs. Wavenumber and Transmittance vs. Wavenumber) alongside the peak detection report and predicted compound name.

### Backend Workflow

1. **File Upload**:
   - The user uploads a CSV file containing spectroscopic data.
   - Supported columns:
     - `wavenumber`
     - `absorbance` or `transmittance`
2. **CSV File Parsing**:
   - Reads user-uploaded CSV files containing IR spectral data.
   - Supports both absorbance and transmittance data formats.
   - Ensures consistent data formatting by handling errors in input, including:
     - Detecting missing or mismatched column headers.
     - Validating and cleaning numerical data by removing non-numeric characters and handling edge cases (e.g., empty or incomplete rows).
     - Converting all data to a uniform numerical format to ensure compatibility with downstream processing.
     - Dynamically parsing mixed headers and inferring data relationships even when unconventional headers are used.


3. **Data Preprocessing**:
   - If `absorbance` is provided, `transmittance` is calculated:
     ```math
     T = 10^{-A} \times 100
     ```
   - If `transmittance` is provided, `absorbance` is calculated:
     ```math
     A = -\log_{10}(T/100)
     ```

4. **Peak Detection**:
   - Uses the **Savitzky-Golay** filter to smooth absorbance data.
   - Detects peaks using the `find_peaks` function and also `savgol_filter` from `scipy.signal`.

5. **Reference Spectrum Matching**:
   - Matches detected peaks with reference functional groups in a reference dataset (`IR_Correlation_Table_5000_to_250.xlsx`).
   - Implements a dynamic grouping and filtering mechanism to extract relevant peaks.

6. **Model Prediction**:
   - Utilizes a **pre-trained Random Forest model** to predict the compound name based on the spectrum.
   - Scales data and ensures compatibility with the model.

7. **Reporting**:
   - The peak detection report categorizes detected peaks by bond type and functional groups.
   - The final compound prediction is returned.

---

## Project Structure

```
userleader_backend
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


---

## Formulas Used

1. **Transmittance to Absorbance Conversion**:
   ```math
   A = -\log_{10}(Transmittance / 100)
   ```

2. **Absorbance to Transmittance Conversion**:
   ```math
   Transmittance = 10^{-A} \times 100
   ```

3. **Peak Center Calculation**:
   - For ranges:
     ```math
     Center = (Low + High) / 2
     ```
   - For uncertainty:
     ```math
     Low = Center - Uncertainty, 
     ```
     ```math
     High = Center + Uncertainty
     ```

---

## Exact Correlation Between Model and Reference Spectrum

1. **Reference Spectrum Role**:
   - Acts as a knowledge base for matching detected peaks to known functional groups.
   - Provides wavenumber ranges, bond types, and functional group associations.

2. **Model Role**:
   - Predicts the compound based on detected peak features.
   - Relies on patterns in wavenumber and transmittance/absorbance.

3. **Interdependence**:
   - Changing the reference spectrum affects peak detection and functional group matching.
   - Example: Removing a functional group (e.g., hydroxyl) from the reference spectrum could lead to incorrect model predictions for compounds containing that group.
---
## Steps to Update Reference Spectrum

1. Update `IR_Correlation_Table_5000_to_250.xlsx` with new wavenumber ranges, bond types, and functional groups.
2. Ensure correct formatting:
   - Columns: `Wavenumbers (cm-1)`, `Bond Type`, `Functional Group`, `Compound`.
3. Restart the application to use the updated reference data.

---

## Limitations

1. **Data Quality**:
   - Poor-quality spectra, such as those with high levels of noise, missing wavenumber ranges, or inconsistent absorbance/transmittance values, can significantly reduce accuracy.
   - Example: A spectrum with significant baseline drift or excessive noise may cause incorrect peak detection or missed peaks altogether, resulting in flawed predictions.

2. **Reference Spectrum Coverage**:
   - The system heavily depends on the completeness and accuracy of the reference spectrum for functional group matching.
   - Example: If the reference spectrum lacks key functional groups or contains outdated wavenumber ranges, it may lead to mismatches or false negatives in the detection process.

3. **Model Generalization**:
   - The **pre-trained model** is optimized for specific training data and may fail to generalize well to compounds or spectra outside its training set.
   - Example: A novel compound with unique spectral features not represented in the training data could result in an inaccurate or uncertain prediction.

4. **Complex Mixtures**:
   - This system is primarily designed for analyzing **single-compound spectra** and may face challenges when dealing with overlapping peaks in mixtures.
   - Example: A spectrum containing two compounds with overlapping wavenumber ranges may lead to ambiguous peak assignments, reducing prediction accuracy.
---
## API Endpoints

### 1. File Upload

- **Endpoint**: `/api/upload/`
- **Method**: `POST`
- **Description**: Upload a CSV file for peak detection and compound prediction.
- **Response**:
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


---
## Conclusion

This system seamlessly integrates reference-based peak matching with machine learning predictions to provide a comprehensive analysis of IR spectra.

