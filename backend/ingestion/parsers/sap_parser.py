import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from records.models import ActivityRecord, IngestionError
from records.constants import SAP_MATERIALS, PLANT_MAPPING, classify_scope

def clean_german_decimal(val_str):
    if not val_str:
        return Decimal('0.0')
    val_str = val_str.strip()
    # German format: 1.234,56 or 1234,56
    if ',' in val_str:
        val_str = val_str.replace('.', '') # Remove thousands separator
        val_str = val_str.replace(',', '.') # Convert decimal comma to dot
    else:
        if val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
    try:
        return Decimal(val_str)
    except InvalidOperation:
        raise ValueError(f"Invalid decimal format: '{val_str}'")

def parse_sap_file(batch, file_content):
    """
    Parses an SAP flat file (CSV).
    Returns (records_to_create, errors_to_create).
    Raises ValueError on fatal structure errors (empty file, missing headers).
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8-sig') # handle BOM if present
        
    csv_file = io.StringIO(file_content)
    reader = csv.reader(csv_file)
    
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("The uploaded file is empty.")

    # Normalize headers
    header_map = {}
    for idx, h in enumerate(headers):
        clean_h = h.strip().lower()
        header_map[clean_h] = idx

    required_headers = ['menge', 'werks', 'datum', 'matnr', 'meins', 'belnr']
    missing = [r for r in required_headers if r not in header_map]
    if missing:
        raise ValueError(f"Missing required SAP headers: {', '.join(missing)}")

    records_to_create = []
    errors_to_create = []

    valid_plants = set(PLANT_MAPPING.keys())
    valid_materials = set(SAP_MATERIALS.keys())
    valid_units = {'L', 'KG', 'M3', 'TO'}

    for row_idx, row in enumerate(reader, start=2): # Headers is row 1
        if not row or all(not cell.strip() for cell in row):
            continue
        
        raw_row_dict = {}
        for h, idx in header_map.items():
            if idx < len(row):
                raw_row_dict[h] = row[idx]

        try:
            # 1. Document Number
            doc_num_idx = header_map['belnr']
            if doc_num_idx >= len(row) or not row[doc_num_idx].strip():
                raise ValueError("Missing document number (Belnr)")
            doc_num = row[doc_num_idx].strip()

            # 2. Material Code
            mat_idx = header_map['matnr']
            if mat_idx >= len(row) or not row[mat_idx].strip():
                raise ValueError("Missing material code (Matnr)")
            mat_code = row[mat_idx].strip().upper()
            if mat_code not in valid_materials:
                raise ValueError(f"Unknown material code (Matnr): '{mat_code}'")
            
            mat_info = SAP_MATERIALS[mat_code]
            category = mat_info['category']

            # 3. Plant Code (Werks)
            plant_idx = header_map['werks']
            if plant_idx >= len(row) or not row[plant_idx].strip():
                raise ValueError("Missing plant code (Werks)")
            plant_code = row[plant_idx].strip()
            
            # Map plant code if in lookup, else store verbatim as required by audit checkpoints
            facility_name = PLANT_MAPPING.get(plant_code, f"Unknown Plant ({plant_code})")

            # 4. Quantity
            qty_idx = header_map['menge']
            if qty_idx >= len(row) or not row[qty_idx].strip():
                raise ValueError("Missing quantity (Menge)")
            quantity_original = clean_german_decimal(row[qty_idx])
            if quantity_original <= 0:
                raise ValueError(f"Quantity (Menge) must be positive: '{row[qty_idx]}'")

            # 5. Date
            date_idx = header_map['datum']
            if date_idx >= len(row) or not row[date_idx].strip():
                raise ValueError("Missing date (Datum)")
            date_str = row[date_idx].strip()
            try:
                parsed_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            except ValueError:
                raise ValueError(f"Invalid date format (Datum): '{date_str}', expected DD.MM.YYYY")

            # 6. Unit
            unit_idx = header_map['meins']
            if unit_idx >= len(row) or not row[unit_idx].strip():
                raise ValueError("Missing unit (Meins)")
            unit_original = row[unit_idx].strip().upper()
            if unit_original not in valid_units:
                raise ValueError(f"Invalid unit (Meins): '{unit_original}', expected L, KG, M3, or TO")

            # Unit Normalization
            unit_norm_map = {
                'L': ('L', Decimal('1.0')),
                'KG': ('kg', Decimal('1.0')),
                'M3': ('m3', Decimal('1.0')),
                'TO': ('tonnes', Decimal('1.0'))
            }
            activity_unit, multiplier = unit_norm_map[unit_original]
            activity_value = quantity_original * multiplier

            # Scope Classification
            scope = classify_scope('SAP', category)

            # Cost center (optional)
            cost_center = ""
            if 'kostl' in header_map:
                cc_idx = header_map['kostl']
                if cc_idx < len(row):
                    cost_center = row[cc_idx].strip()
                    raw_row_dict['cost_center'] = cost_center

            # Add to raw data
            raw_row_dict['facility_name'] = facility_name
            raw_row_dict['document_number'] = doc_num

            rec = ActivityRecord(
                tenant=batch.data_source.tenant,
                batch=batch,
                source_type='SAP',
                scope=scope,
                category=category,
                activity_value=activity_value,
                activity_unit=activity_unit,
                activity_value_original=quantity_original,
                activity_unit_original=unit_original,
                period_start=parsed_date,
                period_end=parsed_date,
                facility_code=plant_code,
                raw_data=raw_row_dict,
                status='PENDING_REVIEW',
                is_locked=False
            )
            records_to_create.append(rec)

        except Exception as e:
            err = IngestionError(
                batch=batch,
                row_number=row_idx,
                raw_row=raw_row_dict,
                error_message=str(e)
            )
            errors_to_create.append(err)

    return records_to_create, errors_to_create
