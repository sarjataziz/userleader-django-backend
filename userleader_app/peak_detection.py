import pandas as pd
import numpy as np
from scipy.signal import find_peaks

def process_reference_data(reference_path, tolerance=0.10):
    reference = pd.read_excel(reference_path)
    required_columns = ['Wavenumbers (cm-1)', 'Group']
    for col in required_columns:
        if col not in reference.columns:
            raise ValueError(f"Reference data must contain '{col}' column.")
    
    # Check if 'Chemical Name' column exists
    has_chemical_name = 'Chemical Name' in reference.columns

    centers = []
    lower_bounds = []
    upper_bounds = []
    groups = []
    chemical_names = []

    for _, row in reference.iterrows():
        wavenumber_value = row['Wavenumbers (cm-1)']
        group = row['Group']
        if has_chemical_name:
            chemical_name = row['Chemical Name']
        else:
            chemical_name = ''

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
            groups.append(group)
            chemical_names.append(chemical_name)
        except ValueError:
            print(f"Unable to process wavenumber value: {wavenumber_str}")
            continue

    processed_reference = pd.DataFrame({
        'Center': centers,
        'Lower Bound': lower_bounds,
        'Upper Bound': upper_bounds,
        'Group': groups
    })
    if has_chemical_name:
        processed_reference['Chemical Name'] = chemical_names
    else:
        processed_reference['Chemical Name'] = [''] * len(processed_reference)

    return processed_reference

def detect_peaks_and_match(wavenumbers, transmittance, reference_data):
    data = pd.DataFrame({
        'wavenumbers': wavenumbers,
        'transmittance': transmittance
    })

    # Invert transmittance for peak detection (since peaks are minima in transmittance)
    data['inverted_transmittance'] = 1 - data['transmittance']

    # Detect peaks
    peaks_indices, _ = find_peaks(data['inverted_transmittance'])
    peaks_data = data.iloc[peaks_indices][['wavenumbers', 'transmittance']]

    # Match peaks to functional groups
    detected_peaks = []
    for _, peak in peaks_data.iterrows():
        wavenumber = peak['wavenumbers']
        transmittance_value = peak['transmittance']

        matched_groups = reference_data[
            (reference_data['Lower Bound'] <= wavenumber) &
            (wavenumber <= reference_data['Upper Bound'])
        ]

        if not matched_groups.empty:
            for _, ref_row in matched_groups.iterrows():
                detected_peaks.append({
                    'wavenumber': wavenumber,
                    'transmittance': transmittance_value,
                    'group': ref_row['Group'],
                    'chemical_name': ref_row['Chemical Name']
                })
        else:
            # Find the closest group
            reference_data['Distance'] = abs(reference_data['Center'] - wavenumber)
            closest_match = reference_data.loc[reference_data['Distance'].idxmin()]
            detected_peaks.append({
                'wavenumber': wavenumber,
                'transmittance': transmittance_value,
                'group': closest_match['Group'] + ' (approximate)',
                'chemical_name': closest_match['Chemical Name']
            })

    return pd.DataFrame(detected_peaks)

def generate_report(detected_peaks):
    report_lines = []

    group_peaks = detected_peaks.groupby('group')

    for group_name, group_data in group_peaks:
        wavenumbers = group_data['wavenumber'].unique()
        wavenumber_list = ', '.join(f"{wn} cm-1" for wn in sorted(wavenumbers))

        chemical_names = group_data['chemical_name'].unique()
        # Remove empty strings and duplicates
        chemical_list = ', '.join(filter(None, chemical_names))

        if 'approximate' in group_name:
            if chemical_list:
                line = f"The peak positions at {wavenumber_list} are approximately assigned to the {group_name} group found in {chemical_list}."
            else:
                line = f"The peak positions at {wavenumber_list} are approximately assigned to the {group_name} group."
        elif group_name == 'Unknown':
            line = f"The peak positions at {wavenumber_list} do not match any known functional group."
        else:
            if chemical_list:
                line = f"The peak positions at {wavenumber_list} represent the {group_name} group found in {chemical_list}."
            else:
                line = f"The peak positions at {wavenumber_list} represent the {group_name} group."
        report_lines.append(line)

    return report_lines

def main():
    # Load user data
    user_file = 'file.csv'  # Replace with the actual user data file
    user_data = pd.read_csv(user_file)
    wavenumbers = user_data['wavenumber']
    transmittance = user_data['transmittance']

    # Process reference data
    reference_path = 'all_in_one.xlsx'  # Replace with your actual reference file path
    reference_data = process_reference_data(reference_path)

    # Detect peaks and match to functional groups
    detected_peaks = detect_peaks_and_match(wavenumbers, transmittance, reference_data)

    # Generate the report
    report = generate_report(detected_peaks)

    # Output the report
    for line in report:
        print(line)

if __name__ == '__main__':
    main()
