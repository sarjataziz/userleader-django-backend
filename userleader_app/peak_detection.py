import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter
import logging
import matplotlib.pyplot as plt  
import traceback

# Initialize logger
logger = logging.getLogger(__name__)

def process_reference_data(reference_path, tolerance=0.10):
    try:
        reference = pd.read_excel(reference_path)
    except FileNotFoundError:
        logger.error(f"Reference file not found at: {reference_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading reference file: {e}")
        raise

    required_columns = ['Wavenumbers (cm-1)', 'Bond Type', 'Functional Group', 'Compound']
    missing_columns = [col for col in required_columns if col not in reference.columns]
    if missing_columns:
        logger.error(f"Missing columns in reference: {', '.join(missing_columns)}")
        raise ValueError(f"Missing columns: {', '.join(missing_columns)}")

    centers, lower_bounds, upper_bounds, bond_types, functional_groups, compounds = [], [], [], [], [], []
    for index, row in reference.iterrows():
        try:
            wavenumber_str = str(row['Wavenumbers (cm-1)']).replace('cm-1', '').strip()
            if '-' in wavenumber_str:
                low, high = map(float, wavenumber_str.split('-'))
                center = (low + high) / 2
            elif '±' in wavenumber_str:
                base, uncertainty = map(float, wavenumber_str.split('±'))
                center, low, high = base, base - uncertainty, base + uncertainty
            else:
                center = float(wavenumber_str)
                low, high = center * (1 - tolerance), center * (1 + tolerance)
            centers.append(center)
            lower_bounds.append(low)
            upper_bounds.append(high)
            bond_types.append(row['Bond Type'])
            functional_groups.append(row['Functional Group'])
            compounds.append(row['Compound'])
        except ValueError as e:
            logger.warning(f"Skipping wavenumber '{row['Wavenumbers (cm-1)']}' at index {index}: {e}")
            continue

    return pd.DataFrame({
        'Center': centers,
        'Lower Bound': lower_bounds,
        'Upper Bound': upper_bounds,
        'Bond Type': bond_types,
        'Functional Group': functional_groups,
        'Compound': compounds
    })

def calculate_transmittance(data):
    data['transmittance'] = (10 ** (-data['absorbance'])) * 100
    return data

def calculate_absorbance(data):
    data['absorbance'] = -np.log10(data['transmittance'] / 100)
    return data

def detect_peaks_and_match(data, reference_data, prominence=0.005):
    data = data.sort_values(by='wavenumber').reset_index(drop=True)

    try:
        window_length = min(len(data), 15)
        if window_length % 2 == 0:
            window_length -= 1
        if window_length < 5:
            raise ValueError("Insufficient data for smoothing")
        data['smoothed_absorbance'] = savgol_filter(data['absorbance'], window_length, polyorder=3)
    except Exception as e:
        logger.warning(f"Smoothing skipped: {e}")
        data['smoothed_absorbance'] = data['absorbance']

    peaks, _ = find_peaks(data['smoothed_absorbance'], prominence=prominence)
    peak_data = data.iloc[peaks].copy().reset_index(drop=True)

    matched_peaks = []
    for _, peak in peak_data.iterrows():
        wavenumber = peak['wavenumber']
        absorbance_value = peak['smoothed_absorbance']
        transmittance_value = 10 ** (-absorbance_value) * 100

        match = reference_data[(reference_data['Lower Bound'] <= wavenumber) & (wavenumber <= reference_data['Upper Bound'])]
        if not match.empty:
            for _, ref_row in match.iterrows():
                matched_peaks.append({
                    'wavenumber': wavenumber,
                    'absorbance': absorbance_value,
                    'transmittance': transmittance_value,
                    'Bond Type': ref_row['Bond Type'],
                    'Functional Group': ref_row['Functional Group'],
                    'Compound': ref_row['Compound']
                })
        else:
            temp_ref = reference_data.copy()
            temp_ref['Distance'] = abs(temp_ref['Center'] - wavenumber)
            closest_match = temp_ref.loc[temp_ref['Distance'].idxmin()]
            matched_peaks.append({
                'wavenumber': wavenumber,
                'absorbance': absorbance_value,
                'transmittance': transmittance_value,
                'Bond Type': closest_match['Bond Type'] + ' (approximate)',
                'Functional Group': closest_match['Functional Group'],
                'Compound': closest_match['Compound']
            })

    return pd.DataFrame(matched_peaks)

def group_and_filter_peaks_dynamic(peaks, group_by='Bond Type', sort_by='wavenumber', top_n=6):
    if peaks.empty:
        return peaks
    if group_by not in peaks.columns or sort_by not in peaks.columns:
        raise ValueError(f"Missing grouping or sorting column in peaks DataFrame")
    grouped = peaks.groupby(group_by, group_keys=False).apply(
        lambda group: group.sort_values(by=sort_by)).reset_index(drop=True)
    return grouped.groupby(group_by, group_keys=False).head(top_n) if top_n else grouped

def generate_report(detected_peaks, report_type='absorbance'):
    if detected_peaks.empty:
        return ["No peaks were detected or matched."]
    report_lines = []
    detected_peaks = detected_peaks.sort_values(by='wavenumber')
    for bond_type, group in detected_peaks.groupby('Bond Type'):
        wn_list = ', '.join(f"{wn:.2f} cm⁻¹" for wn in group['wavenumber'].unique())
        fg_list = ', '.join(group['Functional Group'].dropna().unique())
        if '(approximate)' in bond_type:
            report_lines.append(f"The peak positions at {wn_list} are approximately assigned to the {bond_type} bond type in functional group(s): {fg_list}.")
        else:
            report_lines.append(f"The peak positions at {wn_list} represent the {bond_type} bond type in functional group(s): {fg_list}.")
    return report_lines

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        user_file = './file.csv'
        user_data = pd.read_csv(user_file)

        user_data['wavenumber'] = pd.to_numeric(user_data['wavenumber'], errors='coerce')
        user_data.dropna(subset=['wavenumber'], inplace=True)

        if 'transmittance' in user_data.columns and user_data['transmittance'].max() > 1.5:
            user_data['transmittance'] = user_data['transmittance'] / 100.0

        for col in ['absorbance', 'transmittance']:
            if col in user_data.columns:
                user_data[col] = pd.to_numeric(user_data[col], errors='coerce')

        if 'absorbance' in user_data.columns and 'transmittance' not in user_data.columns:
            logging.info("Calculating transmittance from absorbance.")
            data_df = calculate_transmittance(user_data)
        elif 'transmittance' in user_data.columns and 'absorbance' not in user_data.columns:
            logging.info("Calculating absorbance from transmittance.")
            data_df = calculate_absorbance(user_data)
        elif 'absorbance' in user_data.columns and 'transmittance' in user_data.columns:
            logging.info("Using both absorbance and transmittance.")
            data_df = user_data
        else:
            raise ValueError("File must contain at least one of 'absorbance' or 'transmittance'.")

        reference_path = './userleader_app/data/IR_Correlation_Table_5000_to_250.xlsx'
        reference_data = process_reference_data(reference_path)

        detected_peaks = detect_peaks_and_match(data_df, reference_data)
        grouped_peaks = group_and_filter_peaks_dynamic(detected_peaks)
        report = generate_report(grouped_peaks)

        for line in report:
            print(line)

        plt.figure(figsize=(10, 6))
        plt.plot(data_df['wavenumber'], data_df['absorbance'], label='Absorbance', color='blue')
        plt.xlabel('Wavenumber (cm⁻¹)')
        plt.ylabel('Absorbance')
        plt.title('Absorbance vs. Wavenumber')
        plt.legend()
        plt.gca().invert_xaxis()
        plt.show()

        plt.figure(figsize=(10, 6))
        plt.plot(data_df['wavenumber'], data_df['transmittance'], label='Transmittance', color='red')
        plt.xlabel('Wavenumber (cm⁻¹)')
        plt.ylabel('Transmittance (%)')
        plt.title('Transmittance vs. Wavenumber')
        plt.legend()
        plt.gca().invert_xaxis()
        plt.show()

    except Exception as e:
        logging.error(f"Main execution error: {e}")
        logging.debug(traceback.format_exc())
