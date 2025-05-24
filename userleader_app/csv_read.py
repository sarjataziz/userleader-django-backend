import csv
import numpy as np
import re

y_keywords = [
    'transmittance', 'Transmittance', 'TRANSMITTANCE',
    '%T', '%t', 'Percent Transmittance', 'percent transmittance',
    't', 'T',
    'absorbance', 'Absorbance', 'ABSORBANCE',
    'a', 'A',
    '(micromol/mol)-1m-1 (base 10)'
]

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
        # keep digits, ., -, ±
        cleaned = re.sub(r'[^0-9\.\-\s±eE\+]', '', s)
        try:
            base = cleaned.split('±')[0] if '±' in cleaned else cleaned
            vals.append(float(base))
        except ValueError:
            continue

    if not vals:
        raise ValueError("No valid wavenumber data found.")
    arr = np.array(vals, dtype=float)
    return {
        'wavenumber': arr.tolist(),
        'wavelengths': (1e4 / arr).tolist()
    }

def extract_y(rows, start, idx, header_label):
    vals = []
    for row in rows[start:]:
        if len(row) <= idx: continue
        s = row[idx].strip()
        if not s: continue
        # allow sci notation too
        try:
            vals.append(float(re.sub(r'[^0-9\.\-eE\+]', '', s)))
        except ValueError:
            continue

    if not vals:
        raise ValueError("No valid absorbance or transmittance values found.")
    arr = np.array(vals, dtype=float)
    h = header_label.strip().lower()

    if 'transmittance' in h or '%t' in h:
        arr = np.clip(arr, 0.0, 100.0)
        return {'transmittance': arr.tolist()}

    if 'absorbance' in h or h in ('a',):
        trans = 10 ** (-arr)
        return {'absorbance': arr.tolist(), 'transmittance': trans.tolist()}

    # fallback to %T
    arr = np.clip(arr, 0.0, 100.0)
    return {'transmittance': arr.tolist()}

def csv_read(file_content: str) -> dict:
    """
    1) Try keyword‐based header detection
    2) If none found, fall back to headerless two‐column numeric parse
    """
    rows = list(csv.reader(file_content.splitlines()))
    if len(rows) < 1:
        raise ValueError("CSV file is empty or malformed.")
    
    header_row = None
    for i, row in enumerate(rows[:20]):
        cells = [c.strip().lstrip('\ufeff') for c in row]
        lower = [c.lower() for c in cells]
        if ( any(any(xk.lower() in cell for xk in x_keywords) for cell in lower)
        and any(cell in ('a','t') or any(yk.lower() in cell for yk in y_keywords)
                for cell in lower) ):
            header_row = i
            break

    if header_row is not None:
        header = [c.strip().lstrip('\ufeff') for c in rows[header_row]]
        lower_h = [c.lower() for c in header]
        data = rows[header_row:]  # header + data

        # find indices
        x_idx = y_idx = -1
        for idx, col in enumerate(lower_h):
            if x_idx < 0 and any(xk.lower() == col or xk.lower() in col for xk in x_keywords):
                x_idx = idx
            if y_idx < 0 and (col in ('a','t')
                            or any(yk.lower() == col or yk.lower() in col for yk in y_keywords)):
                if idx != x_idx:
                    y_idx = idx

        if x_idx < 0 or y_idx < 0:
            header_row = None
        else:
            # extract & return
            x_data = extract_x(data, 1, x_idx)
            y_data = extract_y(data, 1, y_idx, header[y_idx])
            n = min(len(x_data['wavenumber']), len(y_data.get('absorbance', y_data['transmittance'])))
            if n == 0:
                raise ValueError("No valid data found in both columns.")
            out = {
                'wavenumber': x_data['wavenumber'][:n],
                'wavelengths': x_data['wavelengths'][:n]
            }
            if 'absorbance' in y_data:
                out['absorbance']    = y_data['absorbance'][:n]
                out['transmittance'] = y_data['transmittance'][:n]
            else:
                out['transmittance'] = y_data['transmittance'][:n]
            return out

    w, t = [], []
    for row in rows:
        if len(row) < 2:
            continue
        # try parse first two entries as floats
        try:
            xval = float(row[0].strip())
            yval = float(row[1].strip())
            w.append(xval)
            t.append(yval)
        except:
            continue

    if not w or not t:
        raise ValueError("Failed to parse CSV file: no two‐column numeric data found.")

    # treat second column as %T by default
    absorbance = -np.log10(np.clip(np.array(t, dtype=float)/100.0, 1e-8, 1.0))
    return {
        'wavenumber': w,
        'wavelengths': (1e4/np.array(w)).tolist(),
        'absorbance': absorbance.tolist(),
        'transmittance': t
    }
