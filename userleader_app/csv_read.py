import csv
import re
import numpy as np
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Define keywords for transmittance and absorbance headers
keywords = [
    'transmittance', 'transmittance %', 't',
    'absorbance', 'a', '(micromol/mol)-1m-1 (base 10)'
]

# Define keywords for wavenumber headers
x_header = [
    'cm-1', 'wavenumber', '1/cm', 'cm^-1', 'wavenumber (cm-1)', 'wavenumber (1/cm)',
    'wavelength (um)', 'wavelength (nm)', 'wavelength', 'nanometers', 'micrometers', 'nm', 'um',
    '1/m', 'm-1', 'm^-1'
]

def extract_x(data, row_number, x_index):
    """
    Extracts the X-axis data (wavenumbers or wavelengths) from the CSV data.

    Args:
        data (list): CSV data as a list of rows.
        row_number (int): Index of the row containing data (after header).
        x_index (int): Index of the X-axis column.

    Returns:
        dict: Dictionary containing 'wavenumber' and/or 'wavelengths'.

    Raises:
        ValueError: If the X-axis header is unknown or data cannot be processed.
    """
    # Extract X column data
    x_column_data = [row[x_index] for row in data[row_number:] if len(row) > x_index]

    # Process header value
    header_value = data[row_number - 1][x_index].strip().lower()

    # Define header options in lowercase
    wavenumber_headers = [h.lower() for h in [
        '1/cm', 'cm-1', 'cm^-1', 'wavenumber', 'wavenumber (1/cm)',
        'wavenumber (cm-1)', 'wavenumber (cm^-1)'
    ]]

    micrometers_headers = [h.lower() for h in ['micrometers', 'um', 'wavelength (um)']]

    nanometers_headers = [h.lower() for h in ['nanometers', 'nm', 'wavelength (nm)']]

    wavenumber_m_headers = [h.lower() for h in [
        '1/m', 'm-1', 'm^-1', 'wavenumber (1/m)',
        'wavenumber (m-1)', 'wavenumber (m^-1)'
    ]]

    x = []
    try:
        if header_value in wavenumber_headers:
            # Process wavenumber data in cm^-1
            for value in x_column_data:
                value_str = value.strip()
                # Remove any unwanted characters except digits, decimal points, minus signs, and '±'
                cleaned_str = re.sub(r'[^\d\.\-\s±]', '', value_str)
                try:
                    # Handle '±' symbol
                    if '±' in cleaned_str:
                        base_value = cleaned_str.split('±')[0].strip()
                    else:
                        base_value = cleaned_str
                    x.append(float(base_value))
                except ValueError:
                    logger.warning(f"Unable to process wavenumber value: '{value_str}'")
                    continue
            x_array = np.array(x)
            return {'wavenumber': x_array.tolist(), 'wavelengths': (1e4 / x_array).tolist()}

        elif header_value in micrometers_headers:
            # Process wavelength data in micrometers
            for value in x_column_data:
                value_str = value.strip()
                try:
                    x.append(float(value_str))
                except ValueError:
                    logger.warning(f"Unable to process wavelength value: '{value_str}'")
                    continue
            x_array = np.array(x)
            return {'wavelengths': x_array.tolist(), 'wavenumber': (1e4 / x_array).tolist()}

        elif header_value in nanometers_headers:
            # Process wavelength data in nanometers
            for value in x_column_data:
                value_str = value.strip()
                try:
                    x.append(float(value_str))
                except ValueError:
                    logger.warning(f"Unable to process wavelength value: '{value_str}'")
                    continue
            x_array = np.array(x)
            return {'wavelengths': x_array.tolist(), 'wavenumber': (1e7 / x_array).tolist()}

        elif header_value in wavenumber_m_headers:
            # Process wavenumber data in m^-1
            for value in x_column_data:
                value_str = value.strip()
                try:
                    x.append(float(value_str))
                except ValueError:
                    logger.warning(f"Unable to process wavenumber value: '{value_str}'")
                    continue
            x_array = np.array(x) * 1e-2  # Convert from 1/m to 1/cm
            return {'wavenumber': x_array.tolist(), 'wavelengths': (1e4 / x_array).tolist()}

        else:
            raise ValueError(f"Unknown X-axis header: '{header_value}'")
    except Exception as e:
        logger.error(f"Error in extract_x: {e}")
        raise ValueError(f"Error processing X-axis data: {e}")

def extract_y(data, row_number, y_index):
    """
    Extracts the Y-axis data (transmittance or absorbance) from the CSV data.

    Args:
        data (list): CSV data as a list of rows.
        row_number (int): Index of the row containing data (after header).
        y_index (int): Index of the Y-axis column.

    Returns:
        dict: Dictionary containing 'transmittance' and/or 'absorbance'.

    Raises:
        ValueError: If the Y-axis header is unknown or data cannot be processed.
    """
    # Extract Y column data
    y_column_data = [row[y_index] for row in data[row_number:] if len(row) > y_index]

    # Convert string values to float
    y = []
    for value in y_column_data:
        value_str = value.strip()
        try:
            y.append(float(value_str))
        except ValueError:
            logger.warning(f"Unable to process Y-axis value: '{value_str}'")
            continue
    y_numeric = np.array(y)

    # Process header value
    header_value = data[row_number - 1][y_index].strip().lower()

    transmittance_headers = [h.lower() for h in ['transmittance', 't', 'transmittance %']]

    absorbance_headers = [h.lower() for h in ['absorbance', 'a']]

    try:
        if header_value in transmittance_headers:
            # Handle percentage transmittance if values are greater than 1
            if y_numeric.max() > 1.0:
                y_numeric = y_numeric / 100.0  # Convert from percentage to fraction
            y_numeric = np.clip(y_numeric, 0.0, 1.0)
            return {'transmittance': y_numeric.tolist()}

        elif header_value in absorbance_headers:
            # Convert absorbance to transmittance
            transmittance = 10 ** (-y_numeric)
            return {'transmittance': transmittance.tolist(), 'absorbance': y_numeric.tolist()}

        else:
            raise ValueError(f"Unknown Y-axis header: '{header_value}'")
    except Exception as e:
        logger.error(f"Error in extract_y: {e}")
        raise ValueError(f"Error processing Y-axis data: {e}")

def csv_read(file_content):
    """
    Reads and processes the CSV file content.

    Args:
        file_content (str): Content of the CSV file as a string.

    Returns:
        dict: Dictionary containing 'wavenumber' and 'transmittance' data.

    Raises:
        ValueError: If required headers are missing or data cannot be processed.
    """
    file_data = {}
    data = list(csv.reader(file_content.splitlines()))
    found_x = False
    found_y = False

    # Convert header keywords to lowercase for case-insensitive matching
    x_header_lower = [header.lower() for header in x_header]
    keywords_lower = [header.lower() for header in keywords]

    for row_number, row in enumerate(data):
        # Skip empty rows
        if not row:
            continue
        # Strip whitespace and convert headers to lowercase
        row_lower = [cell.strip().lower() for cell in row]

        if not found_x and any(keyword in row_lower for keyword in x_header_lower):
            found_x = True
            x_index = row_lower.index(next(keyword for keyword in x_header_lower if keyword in row_lower))

        if not found_y and any(keyword in row_lower for keyword in keywords_lower):
            found_y = True
            y_index = row_lower.index(next(keyword for keyword in keywords_lower if keyword in row_lower))

        if found_x and found_y:
            header_row_number = row_number + 1  # Data starts from next row
            break

    if found_x and found_y:
        x_data = extract_x(data, header_row_number, x_index)
        y_data = extract_y(data, header_row_number, y_index)
        file_data.update(x_data)
        file_data.update(y_data)

        # Ensure data lengths match
        if len(file_data['wavenumber']) != len(file_data['transmittance']):
            min_length = min(len(file_data['wavenumber']), len(file_data['transmittance']))
            file_data['wavenumber'] = file_data['wavenumber'][:min_length]
            file_data['transmittance'] = file_data['transmittance'][:min_length]

        # Sort data by wavenumber
        sorted_indices = np.argsort(file_data['wavenumber'])
        file_data['wavenumber'] = np.array(file_data['wavenumber'])[sorted_indices].tolist()
        file_data['transmittance'] = np.array(file_data['transmittance'])[sorted_indices].tolist()

        return file_data
    else:
        logger.error("Unable to find required headers in the CSV file.")
        raise ValueError("Unable to find required headers in the CSV file.")


