import csv
import numpy as np
import re

# Extended keywords for transmittance and absorbance headers
keywords = [
    'transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T',
    'absorbance', 'Absorbance', 'a', 'A', '(micromol/mol)-1m-1 (base 10)',
    '%T', '%t', 'Percent Transmittance', 'percentT'
]

# Extended keywords for wavenumber headers
x_header = [
    'cm-1', 'wavenumber', 'Wavenumber', '1/cm', 'cm^-1', 'micrometers', 'um', 'wavelength (um)',
    'nanometers', 'nm', 'wavelength (nm)', '1/m', 'm-1', 'm^-1', 'wavenumber (1/m)', 'Wavenumber (1/m)',
    'wavenumber (m-1)', 'wavenumber (m^-1)', 'Wavenumber (m-1)', 'Wavenumber (m^-1)', 'wavenumber (1/cm)',
    'Wavenumber (1/cm)', 'wavenumber (cm-1)', 'wavenumber (cm^-1)', 'Wavenumber (cm-1)', 'Wavenumber (cm^-1)',
    'CM-1', 'cm_1', 'Wavenumber (CM-1)'
]

def extract_x(data, row_number, x_index):
    x = []
    for row in data[row_number:]:
        if len(row) > x_index:
            value = row[x_index].strip()
            if value:
                cleaned_str = re.sub(r'[^\d\.\-\s±]', '', value)
                try:
                    base_value = cleaned_str.split('±')[0].strip() if '±' in cleaned_str else cleaned_str
                    x.append(float(base_value))
                except ValueError:
                    continue
    if not x:
        raise ValueError("No valid wavenumber data found.")
    x_array = np.array(x)
    return {'wavenumber': x_array.tolist(), 'wavelengths': (1e4 / x_array).tolist()}

def extract_y(data, row_number, y_index):
    y = []
    for row in data[row_number:]:
        if len(row) > y_index:
            value = row[y_index].strip()
            if value:
                try:
                    y.append(float(value))
                except ValueError:
                    continue
    if not y:
        raise ValueError("No valid transmittance or absorbance data found.")
    y_numeric = np.array(y)

    header_value = data[row_number - 1][y_index].strip().lower()

    if 'transmittance' in header_value or '%t' in header_value or 'percent' in header_value:
        y_numeric = np.clip(y_numeric, 0.0, 100.0)
        return {'transmittance': y_numeric.tolist()}
    elif 'absorbance' in header_value or header_value in ('a',):
        transmittance = 10 ** (-y_numeric)
        return {'transmittance': transmittance.tolist(), 'absorbance': y_numeric.tolist()}
    else:
        return {'transmittance': y_numeric.tolist()}

def csv_read(file_content):
    file_data = {}
    try:
        data = list(csv.reader(file_content.splitlines()))
        found_x = False
        found_y = False
        x_index = y_index = -1

        x_header_lower = [header.lower() for header in x_header]
        keywords_lower = [header.lower() for header in keywords]

        for row_number, row in enumerate(data, start=1):
            row_lower = [cell.strip().lower() for cell in row]

            x_matches = [i for i, cell in enumerate(row_lower) if any(keyword in cell for keyword in x_header_lower)]
            y_matches = [i for i, cell in enumerate(row_lower) if any(keyword in cell for keyword in keywords_lower)]

            if x_matches:
                x_index = x_matches[0]
                found_x = True
            if y_matches:
                # Pick the first that is not same as x_index
                y_index = y_matches[0] if x_matches[0] != y_matches[0] else (y_matches[1] if len(y_matches) > 1 else -1)
                found_y = y_index != -1

            if found_x and found_y:
                break

        if not found_x or not found_y:
            raise ValueError("Unable to find required headers in the CSV file.")
        if x_index == y_index or x_index == -1 or y_index == -1:
            raise ValueError("Wavenumber and transmittance/absorbance columns cannot be the same or undefined.")

        x_data = extract_x(data, row_number, x_index)
        y_data = extract_y(data, row_number, y_index)
        file_data.update(x_data)
        file_data.update(y_data)

        min_length = min(len(x_data['wavenumber']), len(y_data.get('absorbance', y_data.get('transmittance', []))))
        if min_length == 0:
            raise ValueError("No valid data found in both wavenumber and transmittance/absorbance columns.")

        file_data['wavenumber'] = file_data['wavenumber'][:min_length]
        file_data['wavelengths'] = file_data['wavelengths'][:min_length]
        if 'absorbance' in file_data:
            file_data['absorbance'] = file_data['absorbance'][:min_length]
            file_data['transmittance'] = file_data['transmittance'][:min_length]
        else:
            file_data['transmittance'] = file_data['transmittance'][:min_length]

    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")

    return file_data
