import csv
import numpy as np
import math
import re

# Define keywords for transmittance and absorbance headers
keywords = ['transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T',
            'absorbance', 'Absorbance', 'a', 'A', '(micromol/mol)-1m-1 (base 10)']

# Define keywords for wavenumber headers
x_header = ['cm-1', 'wavenumber', 'Wavenumber', '1/cm', 'cm^-1', 'micrometers', 'um', 'wavelength (um)',
            'nanometers', 'nm', 'wavelength (nm)', '1/m', 'm-1', 'm^-1', 'wavenumber (1/m)', 'Wavenumber (1/m)',
            'wavenumber (m-1)', 'wavenumber (m^-1)', 'Wavenumber (m-1)', 'Wavenumber (m^-1)', 'wavenumber (1/cm)',
            'Wavenumber (1/cm)', 'wavenumber (cm-1)', 'wavenumber (cm^-1)', 'Wavenumber (cm-1)', 'Wavenumber (cm^-1)']

def extract_x(data, row_number, x_index):
    x = []
    for row in data[row_number:]:
        if len(row) > x_index:
            value = row[x_index].strip()
            if value:
                # Remove any unwanted characters except digits, decimal points, minus signs, and spaces
                cleaned_str = re.sub(r'[^\d\.\-\s±]', '', value)
                try:
                    # Handle '±' symbol
                    if '±' in cleaned_str:
                        base_value = cleaned_str.split('±')[0].strip()
                    else:
                        base_value = cleaned_str
                    x.append(float(base_value))
                except ValueError:
                    # Skip invalid values
                    continue
        else:
            continue  # Skip rows with missing x values
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
                    # Skip invalid values
                    continue
        else:
            continue  # Skip rows with missing y values
    if not y:
        raise ValueError("No valid transmittance or absorbance data found.")
    y_numeric = np.array(y)

    header_value = data[row_number - 1][y_index]
    if header_value in ('transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T'):
        # Ensure transmittance values are between 0 and 1
        y_numeric = np.clip(y_numeric, 0.0, 1.0)
        return {'transmittance': y_numeric.tolist()}
    
    elif header_value in ('absorbance', 'Absorbance', 'a', 'A'):
        # Convert absorbance to transmittance
        transmittance = 10 ** (-y_numeric)
        return {'transmittance': transmittance.tolist(), 'absorbance': y_numeric.tolist()}
    
    else:
        return {}

# Modify the header matching to be case-insensitive
def csv_read(file_content):
    file_data = {}
    data = list(csv.reader(file_content.splitlines()))
    found_x = False
    found_y = False

    # Convert header keywords to lowercase for case-insensitive matching
    x_header_lower = [header.lower() for header in x_header]
    keywords_lower = [header.lower() for header in keywords]

    for row_number, row in enumerate(data, start=1):
        # Strip whitespace and convert headers to lowercase
        row_lower = [cell.strip().lower() for cell in row]

        if any(keyword in row_lower for keyword in x_header_lower):
            found_x = True
            x_index = row_lower.index(next(keyword for keyword in x_header_lower if keyword in row_lower))

        if any(keyword in row_lower for keyword in keywords_lower):
            found_y = True
            y_index = row_lower.index(next(keyword for keyword in keywords_lower if keyword in row_lower))

        if found_x and found_y:
            break

    if found_x and found_y:
        x_data = extract_x(data, row_number, x_index)
        y_data = extract_y(data, row_number, y_index)
        file_data.update(x_data)
        file_data.update(y_data)

        # Ensure that wavenumber and y data have the same length
        min_length = min(len(x_data['wavenumber']), len(y_data.get('absorbance', y_data.get('transmittance', []))))
        if min_length == 0:
            raise ValueError("No valid data found in both wavenumber and transmittance/absorbance columns.")
        # Truncate the data to the same length
        x_data['wavenumber'] = x_data['wavenumber'][:min_length]
        x_data['wavelengths'] = x_data['wavelengths'][:min_length]
        if 'absorbance' in y_data:
            y_data['absorbance'] = y_data['absorbance'][:min_length]
            y_data['transmittance'] = y_data['transmittance'][:min_length]
        else:
            y_data['transmittance'] = y_data['transmittance'][:min_length]
        file_data.update(x_data)
        file_data.update(y_data)
    else:
        raise ValueError("Unable to find required headers in the CSV file.")

    return file_data
