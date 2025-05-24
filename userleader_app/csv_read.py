import csv
import numpy as np
import re

# Define keywords for transmittance and absorbance headers
y_keywords = [
    'transmittance', 'Transmittance', 'TRANSMITTANCE',
    '%T', '%t', 'Percent Transmittance', 'percent transmittance',
    't', 'T',
    'absorbance', 'Absorbance', 'ABSORBANCE',
    'a', 'A',
    '(micromol/mol)-1m-1 (base 10)'
]

# Define keywords for wavenumber headers
x_keywords = [
    'cm-1', 'wavenumber', 'Wavenumber', 'WAVENUMBER',
    '1/cm', 'cm^-1',
    '1/m', 'm^-1',
    'wavelength (um)', 'micrometers', 'um',
    'wavelength (nm)', 'nanometers', 'nm',
    'wavenumber (1/m)', 'Wavenumber (1/m)',
    'wavenumber (1/cm)', 'Wavenumber (1/cm)',
    'wavenumber (cm-1)', 'Wavenumber (cm-1)',
    'wavenumber (cm^-1)', 'Wavenumber (cm^-1)',
    'CM-1', 'cm_1', 'Wavenumber (CM-1)'
]

def extract_x(rows, start, idx):
    vals = []
    for row in rows[start:]:
        if len(row) <= idx: continue
        s = row[idx].strip()
        if not s: continue
        cleaned = re.sub(r'[^0-9\.\-\s±]', '', s)
        try:
            base = cleaned.split('±')[0]
            vals.append(float(base))
        except ValueError:
            continue
    if not vals:
        raise ValueError("No valid wavenumber data found.")
    arr = np.array(vals, dtype=float)
    return {
        'wavenumber':  arr.tolist(),
        'wavelengths': (1e4 / arr).tolist()
    }

def extract_y(rows, start, idx, header_label):
    vals = []
    for row in rows[start:]:
        if len(row) <= idx: continue
        s = row[idx].strip()
        if not s: continue
        try:
            vals.append(float(s))
        except ValueError:
            continue
    if not vals:
        raise ValueError("No valid absorbance or transmittance values found.")
    arr = np.array(vals, dtype=float)
    h = header_label.strip().lower()

    if 'transmittance' in h or '%t' in h or h == 't':
        return {'transmittance': arr.tolist()}

    if 'absorbance' in h or h in ('a',):
        trans = 10 ** (-arr)
        return {'absorbance':    arr.tolist(),
                'transmittance': trans.tolist()}
    return {'transmittance': arr.tolist()}

def csv_read(file_content: str) -> dict:
    rows = list(csv.reader(file_content.splitlines()))
    if len(rows) < 1:
        raise ValueError("CSV file is empty or malformed.")

    # Find header row
    header_row = None
    for i, row in enumerate(rows[:20]):
        cells = [c.strip().lstrip('\ufeff') for c in row]
        low = [c.lower() for c in cells]
        has_x = any(any(xk.lower() in cell for xk in x_keywords) for cell in low)
        has_y = any(cell in ('a','t') or any(yk.lower() in cell for yk in y_keywords)
                    for cell in low)
        if has_x and has_y:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Unable to detect valid wavenumber and transmittance/absorbance columns.")

    header = [c.strip().lstrip('\ufeff') for c in rows[header_row]]
    lower_h = [c.lower() for c in header]
    data    = rows[header_row:]  

    x_idx = y_idx = -1
    for idx, col in enumerate(lower_h):
        if x_idx < 0 and any(xk.lower() in col for xk in x_keywords):
            x_idx = idx
        if y_idx < 0 and (col in ('a','t') or any(yk.lower() in col for yk in y_keywords)):
            if idx != x_idx:
                y_idx = idx

    if x_idx < 0 or y_idx < 0 or x_idx == y_idx:
        raise ValueError("Unable to detect valid wavenumber and transmittance/absorbance columns.")

    x_data = extract_x(data, start=1, idx=x_idx)
    y_data = extract_y(data, start=1, idx=y_idx, header_label=header[y_idx])

    n = min(len(x_data['wavenumber']),
            len(y_data.get('absorbance', y_data['transmittance'])))
    if n == 0:
        raise ValueError("No valid data found in both columns.")

    result = {
        'wavenumber':  x_data['wavenumber'][:n],
        'wavelengths': x_data['wavelengths'][:n]
    }
    if 'absorbance' in y_data:
        result['absorbance']    = y_data['absorbance'][:n]
        result['transmittance'] = y_data['transmittance'][:n]
    else:
        result['transmittance'] = y_data['transmittance'][:n]

    return result
