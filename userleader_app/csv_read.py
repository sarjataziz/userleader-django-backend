import csv
import numpy as np
import re

# Keywords for identifying Y-axis: absorbance or transmittance
y_keywords = [
    'transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T',
    'absorbance', 'Absorbance', 'a', 'A', '(micromol/mol)-1m-1 (base 10)',
    '%T', '%t', 'Percent Transmittance', 'percentT'
]

# Keywords for identifying X-axis: wavenumber
x_keywords = [
    'cm-1', 'wavenumber', 'Wavenumber', '1/cm', 'cm^-1', 'micrometers', 'um', 'wavelength (um)',
    'nanometers', 'nm', 'wavelength (nm)', '1/m', 'm-1', 'm^-1', 'wavenumber (1/m)', 'Wavenumber (1/m)',
    'wavenumber (m-1)', 'wavenumber (m^-1)', 'Wavenumber (m-1)', 'Wavenumber (m^-1)', 'wavenumber (1/cm)',
    'Wavenumber (1/cm)', 'wavenumber (cm-1)', 'wavenumber (cm^-1)', 'Wavenumber (cm-1)', 'Wavenumber (cm^-1)',
    'CM-1', 'cm_1', 'Wavenumber (CM-1)'
]

def extract_x(data, start_row, x_index):
    x = []
    for row in data[start_row:]:
        if len(row) > x_index:
            value = row[x_index].strip()
            if value:
                cleaned = re.sub(r'[^\d\.\-\s±]', '', value)
                try:
                    base_value = cleaned.split('±')[0].strip() if '±' in cleaned else cleaned
                    x.append(float(base_value))
                except ValueError:
                    continue
    if not x:
        raise ValueError("No valid wavenumber data found.")
    x_array = np.array(x)
    return {
        'wavenumber': x_array.tolist(),
        'wavelengths': (1e4 / x_array).tolist()
    }
    
def extract_y(data, start_row, y_index, header_label):
    y = []
    for row in data[start_row:]:
        if len(row) > y_index:
            value = row[y_index].strip()
            if value:
                try:
                    y.append(float(value))
                except ValueError:
                    continue
    if not y:
        raise ValueError("No valid absorbance or transmittance values found.")

    y_array = np.array(y)
    header_value = header_label.strip().lower()

    if 'transmittance' in header_value or '%t' in header_value or 'percent' in header_value:
        y_array = np.clip(y_array, 0.0, 100.0)
        return {'transmittance': y_array.tolist()}

    elif 'absorbance' in header_value or header_value in ('a',):
        transmittance = 10 ** (-y_array)
        return {
            'absorbance': y_array.tolist(),
            'transmittance': transmittance.tolist()
        }

    else:
        # Default to transmittance if not identified
        y_array = np.clip(y_array, 0.0, 100.0)
        return {'transmittance': y_array.tolist()}


def csv_read(file_content):
    try:
        data = list(csv.reader(file_content.splitlines()))
        if not data or len(data) < 2:
            raise ValueError("CSV file is empty or malformed.")

        header = [cell.strip() for cell in data[0]]
        lower_header = [cell.lower() for cell in header]

        x_index, y_index = -1, -1
        x_label, y_label = '', ''

        for idx, cell in enumerate(lower_header):
            if x_index == -1 and any(keyword in cell for keyword in x_keywords):
                x_index = idx
                x_label = header[idx]
            elif y_index == -1 and any(keyword in cell for keyword in y_keywords):
                if idx != x_index:
                    y_index = idx
                    y_label = header[idx]

        if x_index == -1 or y_index == -1:
            raise ValueError("Unable to detect valid wavenumber and transmittance/absorbance columns.")
        if x_index == y_index:
            raise ValueError("Wavenumber and transmittance/absorbance columns cannot be the same.")

        x_data = extract_x(data, 1, x_index)
        y_data = extract_y(data, 1, y_index, y_label)

        min_len = min(len(x_data['wavenumber']), len(y_data.get('absorbance', y_data['transmittance'])))
        if min_len == 0:
            raise ValueError("No valid data found in both columns.")

        result = {
            'wavenumber': x_data['wavenumber'][:min_len],
            'wavelengths': x_data['wavelengths'][:min_len]
        }

        if 'absorbance' in y_data:
            result['absorbance'] = y_data['absorbance'][:min_len]
            result['transmittance'] = y_data['transmittance'][:min_len]
        else:
            result['transmittance'] = y_data['transmittance'][:min_len]

        return result

    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
