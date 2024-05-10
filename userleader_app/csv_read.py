import csv
from numpy import array, char, nan, where

keywords = ['transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T',
            'absorbance', 'Absorbance', 'a', 'A', '(micromol/mol)-1m-1 (base 10)']
x_header = ['cm-1', 'wavenumber', 'Wavenumber', '1/cm', 'cm^-1', 'micrometers', 'um', 'wavelength (um)',
            'nanometers', 'nm', 'wavelength (nm)']


def extract_x(data, row_number, x_index):
    # Extract X column data
    x_column_data = [row[x_index] for row in data[row_number:]]

    if data[row_number - 1][x_index] in ('1/cm', 'cm-1', 'cm^-1', 'wavenumber', 'Wavenumber'):
        # Convert wavenumber strings to floats
        x = array(x_column_data, dtype=float)
        return {'wavenumber': x.tolist(), 'wavelengths': (10000.0 / x).tolist()}
    elif data[row_number - 1][x_index] in (
            'micrometers', 'um', 'wavelength (um)', 'nanometers', 'nm', 'wavelength (nm)'):
        # Convert wavelength strings to floats
        x = array(x_column_data, dtype=float)
        return {'wavelengths': x.tolist(), 'wavenumber': (10000.0 / x).tolist()}
    else:
        return {}


def extract_y(data, row_number, y_index):
    # Extract Y column data
    y_column_data = [row[y_index] for row in data[row_number:]]

    # Convert string values to float
    y_numeric = array([float(value) for value in y_column_data])

    if data[row_number - 1][y_index] in ('transmittance', 'Transmittance', 'TRANSMITTANCE', 't', 'T'):
        # Convert unphysical transmittance values to 1.0
        y_numeric[y_numeric > 1.0] = 1.0
        #  Convert to absorbance.
        okay = (y_numeric > 0.0)
        y_numeric[okay] = log10(1.0 / y_numeric[okay])
        y_numeric[logical_not(okay)] = nan

        return {'transmittance': y_numeric.tolist(), 'absorbance': y_numeric.tolist()}
    elif data[row_number - 1][y_index] in ('absorbance', 'Absorbance', 'a', 'A'):
        # Convert absorbance to transmittance
        return {'transmittance': (10 ** (-y_numeric)).tolist(), 'absorbance': y_numeric.tolist()}
    elif data[row_number - 1][y_index] in ('(micromol/mol)-1m-1 (base 10)',):
        # Convert (micromol/mol)^-1m^-1 (base 10) to transmittance
        return {'transmittance': (10 ** (-y_numeric)).tolist(), 'absorbance': y_numeric.tolist()}
    else:
        return {}


def csv_read(file_content):
    file_data = {}
    data = csv.reader(file_content.splitlines())  # Create CSV reader from file content
    data = list(data)  # Store the entire contents of the CSV file
    found_x = False
    found_y = False
    for row_number, row in enumerate(data, start=1):
        if any(keyword in row for keyword in x_header):
            found_x = True
            x_index = row.index([keyword for keyword in x_header if keyword in row][0])

        if any(keyword in row for keyword in keywords):
            found_y = True
            y_index = row.index([keyword for keyword in keywords if keyword in row][0])

        if found_x and found_y:
            break

    if found_x and found_y:
        x_data = extract_x(data, row_number, x_index)
        y_data = extract_y(data, row_number, y_index)
        file_data.update(x_data)
        file_data.update(y_data)
    return file_data
