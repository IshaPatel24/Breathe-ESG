import csv
import io
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from records.models import ActivityRecord, IngestionError
from records.constants import calculate_haversine_distance, classify_scope

def hash_employee_id(emp_id):
    if not emp_id:
        return ""
    salt = "breathe_travel_salt_2026"
    hasher = hashlib.sha256()
    hasher.update((emp_id.strip() + salt).encode('utf-8'))
    return hasher.hexdigest()

def parse_travel_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: '{date_str}'")

def parse_travel_file(batch, file_content):
    """
    Parses corporate travel exports (CSV, Concur/Navan style).
    Returns (records_to_create, errors_to_create).
    Raises ValueError on fatal structure errors (empty file, missing headers).
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8-sig')
        
    csv_file = io.StringIO(file_content)
    reader = csv.reader(csv_file)
    
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("The uploaded file is empty.")

    # Normalize headers
    header_map = {}
    for idx, h in enumerate(headers):
        clean_h = h.strip().lower().replace(' ', '_').replace('/', '_').replace('-', '_')
        header_map[clean_h] = idx

    def get_index_for_aliases(aliases):
        for alias in aliases:
            if alias in header_map:
                return header_map[alias]
        return None

    trip_idx = get_index_for_aliases(['trip_id', 'booking_id', 'id'])
    cat_idx = get_index_for_aliases(['category', 'trip_type', 'type'])
    origin_idx = get_index_for_aliases(['origin', 'departure_airport', 'from'])
    dest_idx = get_index_for_aliases(['destination', 'arrival_airport', 'to'])
    dist_idx = get_index_for_aliases(['distance', 'dist', 'distance_km', 'miles'])
    dist_unit_idx = get_index_for_aliases(['distance_unit', 'unit', 'dist_unit'])
    cabin_idx = get_index_for_aliases(['cabin_class', 'cabin', 'class'])
    start_date_idx = get_index_for_aliases(['check_in_date', 'check_in', 'start_date', 'date', 'trip_date'])
    end_date_idx = get_index_for_aliases(['check_out_date', 'check_out', 'end_date'])
    nights_idx = get_index_for_aliases(['nights', 'number_of_nights', 'room_nights'])
    emp_idx = get_index_for_aliases(['employee_id', 'emp_id', 'employee'])
    cc_idx = get_index_for_aliases(['cost_center', 'department', 'dept'])

    # Validate headers
    missing = []
    if trip_idx is None: missing.append("Trip ID")
    if cat_idx is None: missing.append("Category")
    if start_date_idx is None: missing.append("Start/Check-in Date")
    if emp_idx is None: missing.append("Employee ID")

    if missing:
        raise ValueError(f"Missing required travel headers: {', '.join(missing)}")

    records_to_create = []
    errors_to_create = []

    cat_mapping = {
        'flight': 'flight', 'air': 'flight', 'flights': 'flight',
        'hotel': 'hotel', 'accommodation': 'hotel', 'hotels': 'hotel', 'lodging': 'hotel',
        'car rental': 'car_rental', 'car_rental': 'car_rental', 'car': 'car_rental', 'rental': 'car_rental',
        'rail': 'rail', 'train': 'rail', 'rails': 'rail',
        'taxi': 'taxi_rideshare', 'rideshare': 'taxi_rideshare', 'cab': 'taxi_rideshare', 'uber': 'taxi_rideshare', 'lyft': 'taxi_rideshare', 'ground': 'taxi_rideshare'
    }

    for row_idx, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        
        raw_row_dict = {}
        for h, idx in header_map.items():
            if idx < len(row):
                raw_row_dict[h] = row[idx]

        try:
            # 1. Trip ID
            if trip_idx >= len(row) or not row[trip_idx].strip():
                raise ValueError("Missing Trip ID")
            trip_id = row[trip_idx].strip()

            # 2. Category
            if cat_idx >= len(row) or not row[cat_idx].strip():
                raise ValueError("Missing Category")
            raw_category = row[cat_idx].strip().lower()
            category = cat_mapping.get(raw_category)
            if not category:
                raise ValueError(f"Unknown or unsupported travel category: '{raw_category}'")

            # 3. Employee ID (Anonymize!)
            if emp_idx >= len(row) or not row[emp_idx].strip():
                raise ValueError("Missing Employee ID")
            emp_id_raw = row[emp_idx].strip()
            employee_hash = hash_employee_id(emp_id_raw)
            raw_row_dict['employee_id'] = emp_id_raw

            # 4. Dates
            if start_date_idx >= len(row) or not row[start_date_idx].strip():
                raise ValueError("Missing Start/Check-in Date")
            period_start = parse_travel_date(row[start_date_idx])
            
            period_end = period_start
            if end_date_idx is not None and end_date_idx < len(row) and row[end_date_idx].strip():
                period_end = parse_travel_date(row[end_date_idx])

            if period_start > period_end:
                raise ValueError(f"Start date {period_start} cannot be after End date {period_end}")

            # 5. Cost Center
            cost_center = ""
            if cc_idx is not None and cc_idx < len(row):
                cost_center = row[cc_idx].strip()

            # Process based on Category
            activity_value = Decimal('0.0')
            activity_unit = ""
            activity_value_original = Decimal('0.0')
            activity_unit_original = ""
            status = 'PENDING_REVIEW'
            flag_reason = None

            facility_code = "TRAVEL_CORP"

            if category == 'hotel':
                activity_unit = 'nights'
                nights = None
                if nights_idx is not None and nights_idx < len(row) and row[nights_idx].strip():
                    try:
                        nights = Decimal(row[nights_idx].strip())
                    except InvalidOperation:
                        pass
                
                if nights is None:
                    delta = period_end - period_start
                    nights = Decimal(delta.days)
                
                if nights <= 0:
                    raise ValueError(f"Hotel nights must be positive: got {nights}")
                
                activity_value = nights
                activity_value_original = nights
                activity_unit_original = 'nights'
                
                if dest_idx is not None and dest_idx < len(row) and row[dest_idx].strip():
                    facility_code = row[dest_idx].strip()

            elif category == 'flight':
                activity_unit = 'km'
                origin = ""
                destination = ""
                if origin_idx is not None and origin_idx < len(row):
                    origin = row[origin_idx].strip().upper()
                if dest_idx is not None and dest_idx < len(row):
                    destination = row[dest_idx].strip().upper()
                
                if not origin or not destination:
                    raise ValueError(f"Flight must have both Origin and Destination IATA codes: origin='{origin}', destination='{destination}'")

                # Get distance
                distance_val = None
                raw_dist_str = ""
                if dist_idx is not None and dist_idx < len(row) and row[dist_idx].strip():
                    raw_dist_str = row[dist_idx].strip()
                    try:
                        distance_val = Decimal(raw_dist_str)
                    except InvalidOperation:
                        pass
                
                unit_orig = 'km'
                if dist_unit_idx is not None and dist_unit_idx < len(row) and row[dist_unit_idx].strip():
                    unit_orig = row[dist_unit_idx].strip().lower()

                # If missing distance, calculate great-circle fallback
                if distance_val is None or distance_val <= 0:
                    gc_distance = calculate_haversine_distance(origin, destination)
                    if gc_distance is not None:
                        distance_val = Decimal(str(gc_distance))
                        unit_orig = 'km'
                        raw_row_dict['distance_calculated'] = True
                    else:
                        distance_val = Decimal('0.0')
                        unit_orig = 'km'
                        status = 'FLAGGED'
                        flag_reason = f"Unknown IATA codes '{origin}' to '{destination}' for great-circle distance calculation."
                
                # Normalization to km
                is_miles = any(m in unit_orig for m in ['mile', 'mi', 'mil'])
                if is_miles:
                    activity_value = distance_val * Decimal('1.60934')
                else:
                    activity_value = distance_val
                
                activity_value_original = distance_val
                activity_unit_original = 'miles' if is_miles else 'km'
                facility_code = f"{origin}-{destination}"

                # Cabin class (store raw)
                cabin_class = ""
                if cabin_idx is not None and cabin_idx < len(row):
                    cabin_class = row[cabin_idx].strip()
                    raw_row_dict['cabin_class'] = cabin_class

            else: # Ground
                activity_unit = 'km'
                distance_val = Decimal('0.0')
                unit_orig = 'km'
                
                if dist_idx is not None and dist_idx < len(row) and row[dist_idx].strip():
                    try:
                        distance_val = Decimal(row[dist_idx].strip())
                    except InvalidOperation:
                        pass
                        
                if dist_unit_idx is not None and dist_unit_idx < len(row) and row[dist_unit_idx].strip():
                    unit_orig = row[dist_unit_idx].strip().lower()

                is_miles = any(m in unit_orig for m in ['mile', 'mi', 'mil'])
                if is_miles:
                    activity_value = distance_val * Decimal('1.60934')
                else:
                    activity_value = distance_val

                activity_value_original = distance_val
                activity_unit_original = 'miles' if is_miles else 'km'
                
                if origin_idx is not None and origin_idx < len(row) and row[origin_idx].strip():
                    facility_code = row[origin_idx].strip()

            # Hash Employee ID and add metadata to raw_data
            raw_row_dict['employee_id_hash'] = employee_hash
            raw_row_dict['trip_id'] = trip_id
            raw_row_dict['cost_center'] = cost_center
            raw_row_dict['category_normalized'] = category
            
            # Clean original employee id
            if 'employee_id' in raw_row_dict:
                raw_row_dict['employee_id'] = '[ANONYMIZED]'
            if 'emp_id' in raw_row_dict:
                raw_row_dict['emp_id'] = '[ANONYMIZED]'
            if 'employee' in raw_row_dict:
                raw_row_dict['employee'] = '[ANONYMIZED]'

            # Scope classification
            scope = classify_scope('TRAVEL', category)

            rec = ActivityRecord(
                tenant=batch.data_source.tenant,
                batch=batch,
                source_type='TRAVEL',
                scope=scope,
                category=category,
                activity_value=activity_value,
                activity_unit=activity_unit,
                activity_value_original=activity_value_original,
                activity_unit_original=activity_unit_original,
                period_start=period_start,
                period_end=period_end,
                facility_code=facility_code,
                raw_data=raw_row_dict,
                status=status,
                flag_reason=flag_reason,
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
