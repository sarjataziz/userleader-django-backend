import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter
import logging
import matplotlib.pyplot as plt  

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

def calculate_transmittance(data):
    """
    Calculate Transmittance (%) from Absorbance.

    Args:
        data (pd.DataFrame): DataFrame with 'wavenumber' and 'absorbance'.

    Returns:
        pd.DataFrame: Updated DataFrame with 'transmittance'.
    """
    data['transmittance'] = (10 ** (-data['absorbance'])) * 100
    return data

def calculate_absorbance(data):
    """
    Calculate Absorbance from Transmittance.

    Args:
        data (pd.DataFrame): DataFrame with 'wavenumber' and 'transmittance'.

    Returns:
        pd.DataFrame: Updated DataFrame with 'absorbance'.
    """
    data['absorbance'] = -np.log10(data['transmittance'] / 100)
    return data

def detect_peaks_and_match(data, reference_data, prominence=0.005):
    """
    Detect peaks in Absorbance data and match to reference data.

    Args:
        data (pd.DataFrame): DataFrame with 'wavenumber' and 'absorbance'.
        reference_data (pd.DataFrame): Processed reference data.
        prominence (float): Prominence parameter for peak detection.

    Returns:
        pd.DataFrame: Detected peaks with matching functional groups.
    """
    # Ensure data is sorted by wavenumber in ascending order
    data = data.sort_values(by='wavenumber').reset_index(drop=True)

    # Smooth the absorbance data
    window_length = 15 if len(data) >= 15 else len(data) - (len(data) % 2 == 0)
    if window_length < 5:
        window_length = 5  # Minimum window length
    data['smoothed_absorbance'] = savgol_filter(
        data['absorbance'], window_length=window_length, polyorder=3
    )

    # Detect peaks in the smoothed absorbance data
    peaks, properties = find_peaks(
        data['smoothed_absorbance'],
        prominence=prominence
    )
    peak_data = data.iloc[peaks].copy()
    peak_data.reset_index(drop=True, inplace=True)

    matched_peaks = []

    for idx, peak in peak_data.iterrows():
        wavenumber = peak['wavenumber']
        absorbance_value = peak['smoothed_absorbance']

        # Calculate transmittance for the peak
        transmittance_value = 10 ** (-absorbance_value) * 100

        # Match peak to reference data within the specified tolerance
        matches = reference_data[
            (reference_data['Lower Bound'] <= wavenumber) &
            (wavenumber <= reference_data['Upper Bound'])
        ]

        if not matches.empty:
            # Exact match: Add all matches within the range
            for _, ref_row in matches.iterrows():
                matched_peaks.append({
                    'wavenumber': wavenumber,
                    'absorbance': absorbance_value,
                    'transmittance': transmittance_value,
                    'Bond Type': ref_row['Bond Type'],
                    'Functional Group': ref_row['Functional Group'],
                    'Compound': ref_row['Compound']
                })
        else:
            # Approximate match: Find the closest match outside the range
            reference_data['Distance'] = abs(reference_data['Center'] - wavenumber)
            closest_match = reference_data.loc[reference_data['Distance'].idxmin()]
            matched_peaks.append({
                'wavenumber': wavenumber,
                'absorbance': absorbance_value,
                'transmittance': transmittance_value,
                'Bond Type': closest_match['Bond Type'] + ' (approximate)',
                'Functional Group': closest_match['Functional Group'],
                'Compound': closest_match['Compound']
            })
            reference_data.drop(columns=['Distance'], inplace=True)

    matched_peaks_df = pd.DataFrame(matched_peaks)

    return matched_peaks_df

def group_and_filter_peaks_dynamic(peaks, group_by='Bond Type', sort_by='wavenumber', top_n=6):
    """
    Dynamically group and filter detected peaks based on specified criteria.

    Args:
        peaks (pd.DataFrame): DataFrame containing detected peaks.
        group_by (str): Column name to group peaks by.
        sort_by (str): Column name to sort peaks within each group.
        top_n (int or None): Number of top peaks to retain for each group. If None, all peaks are retained.

    Returns:
        pd.DataFrame: Filtered DataFrame with peaks grouped and sorted.
    """
    if peaks.empty:
        return peaks

    # Validate input parameters
    if group_by not in peaks.columns:
        raise ValueError(f"Grouping column '{group_by}' not found in the DataFrame.")
    if sort_by not in peaks.columns:
        raise ValueError(f"Sorting column '{sort_by}' not found in the DataFrame.")

    # Group and sort peaks
    grouped_peaks = peaks.groupby(group_by, group_keys=False).apply(
        lambda group: group.sort_values(by=sort_by, ascending=True)
    ).reset_index(drop=True)

    if top_n is not None:
        # Retain only top N peaks per group
        grouped_peaks = grouped_peaks.groupby(group_by, group_keys=False).head(top_n)

    return grouped_peaks

def generate_report(detected_peaks, report_type='absorbance'):
    """
    Generates a report based on the detected peaks.

    Args:
        detected_peaks (pd.DataFrame): DataFrame containing detected peaks and their matches.
        report_type (str): 'absorbance' or 'transmittance' to indicate which data to include.

    Returns:
        list: List of report lines.
    """
    if detected_peaks.empty:
        return ["No peaks were detected or matched to the reference data."]

    report_lines = []

    # Group peaks by 'Bond Type' and sort wavenumbers ascending
    detected_peaks = detected_peaks.sort_values(by='wavenumber', ascending=True)
    group_peaks = detected_peaks.groupby('Bond Type', sort=False)

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

    # Load user data
    user_file = './file.csv'   
    user_data = pd.read_csv(user_file)

    # Check and ensure both columns are available
    if 'absorbance' in user_data.columns and 'transmittance' not in user_data.columns:
        logging.info("Transmittance not found. Calculating it from absorbance.")
        data_df = calculate_transmittance(user_data)
    elif 'transmittance' in user_data.columns and 'absorbance' not in user_data.columns:
        logging.info("Absorbance not found. Calculating it from transmittance.")
        data_df = calculate_absorbance(user_data)
    elif 'absorbance' in user_data.columns and 'transmittance' in user_data.columns:
        logging.info("Both 'absorbance' and 'transmittance' columns found. Using both.")
        data_df = user_data 
    else:
        raise ValueError("Input data must contain at least one of 'absorbance' or 'transmittance'.")



    # Process reference data
    reference_path = './userleader_app/data/IR_Correlation_Table_5000_to_250.xlsx' 
    reference_data = process_reference_data(reference_path)

    # Detect peaks and match to functional groups
    detected_peaks = detect_peaks_and_match(data_df, reference_data, prominence=0.005)

    # Group and filter peaks
    grouped_peaks = group_and_filter_peaks_dynamic(detected_peaks, group_by='Bond Type', sort_by='wavenumber')

    # Generate the report
    report = generate_report(grouped_peaks)

    # Output the report
    for line in report:
        print(line)

    # Plotting Absorbance vs. Wavenumber
    plt.figure(figsize=(10, 6))
    plt.plot(data_df['wavenumber'], data_df['absorbance'], label='Absorbance', color='blue')
    plt.xlabel('Wavenumber (cm⁻¹)')
    plt.ylabel('Absorbance')
    plt.title('Absorbance vs. Wavenumber')
    plt.legend()
    plt.gca().invert_xaxis()  
    plt.show()

    # Plotting Transmittance vs. Wavenumber
    plt.figure(figsize=(10, 6))
    plt.plot(data_df['wavenumber'], data_df['transmittance'], label='Transmittance', color='red')
    plt.xlabel('Wavenumber (cm⁻¹)')
    plt.ylabel('Transmittance (%)')
    plt.title('Transmittance vs. Wavenumber')
    plt.legend()
    plt.gca().invert_xaxis()  
    plt.show()
