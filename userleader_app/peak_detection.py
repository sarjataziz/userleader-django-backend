import pandas as pd
import numpy as np
from scipy.signal import find_peaks, savgol_filter
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def process_reference_data(reference_path, tolerance=0.05):
    """
    Processes the reference data from the given Excel file.

    Args:
        reference_path (str): Path to the reference Excel file.
        tolerance (float): Tolerance percentage for matching wavenumbers.

    Returns:
        pd.DataFrame: Processed reference data with calculated bounds.

    Raises:
        FileNotFoundError: If the reference file is not found.
        ValueError: If required columns are missing or data cannot be processed.
    """
    # Read the reference Excel file
    try:
        reference = pd.read_excel(reference_path)
    except FileNotFoundError:
        logger.error(f"Reference file not found at: {reference_path}")
        raise FileNotFoundError(f"Reference file not found at: {reference_path}")
    except Exception as e:
        logger.error(f"Error reading reference file: {e}")
        raise Exception(f"Error reading reference file: {e}")
    
    # Ensure required columns are present
    required_columns = ['Wavenumbers (cm-1)', 'Bond Type', 'Functional Group', 'Compound']
    missing_columns = [col for col in required_columns if col not in reference.columns]
    if missing_columns:
        logger.error(f"Reference data must contain the following columns: {', '.join(missing_columns)}")
        raise ValueError(f"Reference data must contain the following columns: {', '.join(missing_columns)}")
    
    # Initialize lists to store processed data
    centers = []
    lower_bounds = []
    upper_bounds = []
    bond_types = []
    functional_groups = []
    compounds = []

    for index, row in reference.iterrows():
        wavenumber_value = row['Wavenumbers (cm-1)']
        bond_type = row['Bond Type']
        functional_group = row['Functional Group']
        compound = row['Compound']

        wavenumber_str = str(wavenumber_value).replace('cm-1', '').strip()
        try:
            if '-' in wavenumber_str:
                low_str, high_str = wavenumber_str.split('-')
                low = float(low_str.strip())
                high = float(high_str.strip())
                center = (low + high) / 2
            elif '±' in wavenumber_str:
                base_value, uncertainty = wavenumber_str.split('±')
                center = float(base_value.strip())
                uncertainty = float(uncertainty.strip())
                low = center - uncertainty
                high = center + uncertainty
            else:
                center = float(wavenumber_str.strip())
                low = center * (1 - tolerance)
                high = center * (1 + tolerance)
            
            centers.append(center)
            lower_bounds.append(low)
            upper_bounds.append(high)
            bond_types.append(bond_type)
            functional_groups.append(functional_group)
            compounds.append(compound)
        except ValueError as e:
            logger.warning(f"Unable to process wavenumber value '{wavenumber_value}' at index {index}: {e}")
            continue

    processed_reference = pd.DataFrame({
        'Center': centers,
        'Lower Bound': lower_bounds,
        'Upper Bound': upper_bounds,
        'Bond Type': bond_types,
        'Functional Group': functional_groups,
        'Compound': compounds
    })

    return processed_reference

def detect_peaks_and_match(wavenumbers, transmittance, reference_data, prominence=0.02):
    """
    Detects peaks in the transmittance data and matches them to the reference data.

    Args:
        wavenumbers (list): List of wavenumbers from user data.
        transmittance (list): List of transmittance values from user data.
        reference_data (pd.DataFrame): Processed reference data.
        prominence (float): Minimum prominence of peaks to detect.

    Returns:
        pd.DataFrame: DataFrame containing detected peaks and their matches.
    """
    data = pd.DataFrame({
        'wavenumber': wavenumbers,
        'transmittance': transmittance
    })

    # Validate data
    if data['wavenumber'].isnull().any() or data['transmittance'].isnull().any():
        raise ValueError("User data contains null values.")

    # Sort data by wavenumber in ascending order for correct smoothing
    data = data.sort_values(by='wavenumber')

    # Invert transmittance for peak detection (since peaks are minima in transmittance)
    data['inverted_transmittance'] = 1 - data['transmittance']

    # Apply Savitzky-Golay filter for smoothing
    try:
        window_length = 11 if len(data) >= 11 else len(data) - (len(data) % 2 == 0)
        if window_length < 5:
            window_length = 5  # Minimum window length
        data['smoothed_transmittance'] = savgol_filter(
            data['inverted_transmittance'], window_length=window_length, polyorder=3
        )
    except Exception as e:
        logger.error(f"Error during data smoothing: {e}")
        raise Exception(f"Error during data smoothing: {e}")

    # Detect peaks
    peaks_indices, properties = find_peaks(data['smoothed_transmittance'], prominence=prominence)
    peaks_data = data.iloc[peaks_indices][['wavenumber', 'transmittance']]

    # Match peaks to reference data
    detected_peaks = []
    for _, peak in peaks_data.iterrows():
        wavenumber = peak['wavenumber']
        transmittance_value = peak['transmittance']

        # Check if the peak falls within any reference range
        matched_entries = reference_data[
            (reference_data['Lower Bound'] <= wavenumber) &
            (wavenumber <= reference_data['Upper Bound'])
        ]

        if not matched_entries.empty:
            # Exact match: Add all matches within the range
            for _, ref_row in matched_entries.iterrows():
                detected_peaks.append({
                    'wavenumber': wavenumber,
                    'transmittance': transmittance_value,
                    'Bond Type': ref_row['Bond Type'],
                    'Functional Group': ref_row['Functional Group'],
                    'Compound': ref_row['Compound']
                })
        else:
            # Approximate match: Find the closest match outside the range
            reference_data['Distance'] = abs(reference_data['Center'] - wavenumber)
            closest_match = reference_data.loc[reference_data['Distance'].idxmin()]
            detected_peaks.append({
                'wavenumber': wavenumber,
                'transmittance': transmittance_value,
                'Bond Type': closest_match['Bond Type'] + ' (approximate)',
                'Functional Group': closest_match['Functional Group'],
                'Compound': closest_match['Compound']
            })

    # Clean up temporary 'Distance' column if it exists
    if 'Distance' in reference_data.columns:
        reference_data.drop(columns=['Distance'], inplace=True)

    return pd.DataFrame(detected_peaks)

def generate_report(detected_peaks):
    """
    Generates a report based on the detected peaks.

    Args:
        detected_peaks (pd.DataFrame): DataFrame containing detected peaks and their matches.

    Returns:
        list: List of report lines.
    """
    if detected_peaks.empty:
        return ["No peaks were detected or matched to the reference data."]

    report_lines = []

    # Group peaks by 'Bond Type' and sort wavenumbers
    detected_peaks = detected_peaks.sort_values(by='wavenumber', ascending=False)
    group_peaks = detected_peaks.groupby('Bond Type')

    for bond_type, group_data in group_peaks:
        wavenumbers = group_data['wavenumber'].unique()
        wavenumber_list = ', '.join(f"{wn:.2f} cm⁻¹" for wn in wavenumbers)
        functional_groups = group_data['Functional Group'].unique()
        functional_group_list = ', '.join(filter(None, functional_groups))

        if '(approximate)' in bond_type:
            line = f"The peak positions at {wavenumber_list} are approximately assigned to the {bond_type} bond type found in functional group(s): {functional_group_list}."
        else:
            line = f"The peak positions at {wavenumber_list} represent the {bond_type} bond type in functional group(s): {functional_group_list}."

        report_lines.append(line)

    return report_lines

# Main function for testing
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Load user data (replace with actual file paths)
    user_file = './file.csv'   
    user_data = pd.read_csv(user_file)
    wavenumbers = user_data['wavenumber']
    transmittance = user_data['transmittance']

    # Process reference data
    reference_path = './userleader_app/data/IR_Correlation_Table_5000_to_250.xlsx' 
    reference_data = process_reference_data(reference_path)

    # Detect peaks and match to functional groups
    detected_peaks = detect_peaks_and_match(wavenumbers, transmittance, reference_data, prominence=0.02)

    # Generate the report
    report = generate_report(detected_peaks)

    # Output the report
    for line in report:
        print(line)
