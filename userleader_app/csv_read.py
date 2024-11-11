import csv
import numpy as np
import math
import re

keywords = ['transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T',
            'absorbance', 'Absorbance', 'a', 'A', '(micromol/mol)-1m-1 (base 10)']
x_header = ['cm-1', 'wavenumber', 'Wavenumber', '1/cm', 'cm^-1', 'micrometers', 'um', 'wavelength (um)',
            'nanometers', 'nm', 'wavelength (nm)', '1/m', 'm-1', 'm^-1', 'wavenumber (1/m)', 'Wavenumber (1/m)',
            'wavenumber (m-1)', 'wavenumber (m^-1)', 'Wavenumber (m-1)', 'Wavenumber (m^-1)', 'wavenumber (1/cm)',
            'Wavenumber (1/cm)',
            'wavenumber (cm-1)', 'wavenumber (cm^-1)', 'Wavenumber (cm-1)', 'Wavenumber (cm^-1)']

def extract_x(data, row_number, x_index):
    # Extract X column data
    x_column_data = [row[x_index] for row in data[row_number:]]

    header_value = data[row_number - 1][x_index]
    if header_value in (
            '1/cm', 'cm-1', 'cm^-1', 'wavenumber', 'Wavenumber', 'wavenumber (1/cm)', 'Wavenumber (1/cm)',
            'wavenumber (cm-1)', 'wavenumber (cm^-1)', 'Wavenumber (cm-1)', 'Wavenumber (cm^-1)'):
        x = []
        for value in x_column_data:
            value_str = value.strip()
            # Remove any unwanted characters except digits, decimal points, minus signs, and spaces
            cleaned_str = re.sub(r'[^\d\.\-\s±]', '', value_str)
            try:
                if '±' in cleaned_str:
                    base_value = cleaned_str.split('±')[0].strip()
                else:
                    base_value = cleaned_str
                x.append(float(base_value))
            except ValueError:
                raise ValueError(f"Unable to process wavenumber value: '{value_str}'")
        x_array = np.array(x)
        return {'wavenumber': x_array.tolist()}
    else:
        return {}

def extract_y(data, row_number, y_index):
    # Extract Y column data
    y_column_data = [row[y_index] for row in data[row_number:]]

    # Convert string values to float
    y = []
    for value in y_column_data:
        value_str = value.strip()
        try:
            y.append(float(value_str))
        except ValueError:
            raise ValueError(f"Unable to process transmittance value: '{value_str}'")
    y_numeric = np.array(y)

    if data[row_number - 1][y_index] in ('transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T'):
        # Ensure transmittance values are between 0 and 1
        y_numeric = np.clip(y_numeric, 0.0, 1.0)
        return {'transmittance': y_numeric.tolist()}
    elif data[row_number - 1][y_index] in ('absorbance', 'Absorbance', 'a', 'A'):
        # Convert absorbance to transmittance
        transmittance = 10 ** (-y_numeric)
        return {'transmittance': transmittance.tolist()}
    else:
        return {}

def csv_read(file_content):
    file_data = {}
    data = csv.reader(file_content.splitlines())
    data = list(data)
    found_x = False
    found_y = False
    for row_number, row in enumerate(data, start=1):
        if any(keyword in row for keyword in x_header):
            found_x = True
            x_index = row.index(next(keyword for keyword in x_header if keyword in row))

        if any(keyword in row for keyword in keywords):
            found_y = True
            y_index = row.index(next(keyword for keyword in keywords if keyword in row))

        if found_x and found_y:
            break

    if found_x and found_y:
        x_data = extract_x(data, row_number, x_index)
        y_data = extract_y(data, row_number, y_index)
        file_data.update(x_data)
        file_data.update(y_data)
    else:
        raise ValueError("Unable to find required headers in the CSV file.")

    return file_data
