import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils.dateparse import parse_date
from records.models import ActivityRecord, IngestionError
from records.constants import UTILITY_SITE_MAPPING, classify_scope

def parse_date_flexible(date_str):
    if not date_str:
        raise ValueError("Date string is empty")
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: '{date_str}'")

def parse_utility_file(batch, file_content):
    """
    Parses a utility portal electricity export (CSV).
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

    meter_idx = get_index_for_aliases(['meter_id', 'account_number', 'meter_no'])
    start_idx = get_index_for_aliases(['billing_start', 'start_date', 'billing_period_start'])
    end_idx = get_index_for_aliases(['billing_end', 'end_date', 'billing_period_end'])
    unit_idx = get_index_for_aliases(['unit', 'unit_original', 'energy_unit'])
    site_idx = get_index_for_aliases(['site', 'location', 'site_name', 'facility'])
    
    consumption_idx = get_index_for_aliases(['consumption', 'usage', 'consumed_kwh', 'kwh_consumed'])
    curr_reading_idx = get_index_for_aliases(['current_reading', 'curr_reading', 'reading'])
    prev_reading_idx = get_index_for_aliases(['previous_reading', 'prev_reading', 'prev_read'])
    tariff_idx = get_index_for_aliases(['tariff', 'rate_plan', 'tariff_name'])

    # Validation of headers
    missing = []
    if meter_idx is None: missing.append("Meter ID")
    if start_idx is None: missing.append("Billing Start Date")
    if end_idx is None: missing.append("Billing End Date")
    if site_idx is None: missing.append("Site / Location")
    if unit_idx is None: missing.append("Unit")
    if consumption_idx is None and curr_reading_idx is None:
        missing.append("Consumption or Current Reading")

    if missing:
        raise ValueError(f"Missing required utility headers: {', '.join(missing)}")

    records_to_create = []
    errors_to_create = []

    valid_units = {'KWH', 'MWH', 'KVAH'}

    for row_idx, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        
        raw_row_dict = {}
        for h, idx in header_map.items():
            if idx < len(row):
                raw_row_dict[h] = row[idx]

        try:
            # 1. Meter ID
            if meter_idx >= len(row) or not row[meter_idx].strip():
                raise ValueError("Missing Meter ID")
            meter_id = row[meter_idx].strip()

            # 2. Billing Period
            if start_idx >= len(row) or not row[start_idx].strip():
                raise ValueError("Missing Billing Start Date")
            if end_idx >= len(row) or not row[end_idx].strip():
                raise ValueError("Missing Billing End Date")
            
            period_start = parse_date_flexible(row[start_idx])
            period_end = parse_date_flexible(row[end_idx])
            if period_start > period_end:
                raise ValueError(f"Start date {period_start} cannot be after end date {period_end}")

            # 3. Site/Location
            if site_idx >= len(row) or not row[site_idx].strip():
                raise ValueError("Missing Site/Location identifier")
            site_raw = row[site_idx].strip()
            
            # Map site identifier to facility code (or use raw value if not found)
            facility_code = site_raw
            facility_name = site_raw
            for key, val in UTILITY_SITE_MAPPING.items():
                if key.lower() == site_raw.lower():
                    facility_name = val
                    facility_code = key
                    break
            
            # 4. Energy Unit
            if unit_idx >= len(row) or not row[unit_idx].strip():
                raise ValueError("Missing Unit")
            unit_original = row[unit_idx].strip().upper()
            if unit_original not in valid_units:
                raise ValueError(f"Invalid unit: '{unit_original}'. Expected KWH, MWH, or KVAH")

            # 5. Tariff (optional)
            tariff = ""
            if tariff_idx is not None and tariff_idx < len(row):
                tariff = row[tariff_idx].strip()
                raw_row_dict['tariff'] = tariff

            # 6. Consumption calculation (either direct or cumulative delta)
            consumption_val = None
            reading_type = 'consumption'
            
            # Scenario A: Previous and Current Reading provided in this row
            if curr_reading_idx is not None and curr_reading_idx < len(row) and row[curr_reading_idx].strip() and \
               prev_reading_idx is not None and prev_reading_idx < len(row) and row[prev_reading_idx].strip():
                try:
                    curr_read = Decimal(row[curr_reading_idx].strip())
                    prev_read = Decimal(row[prev_reading_idx].strip())
                    if curr_read < prev_read:
                        raise ValueError(f"Current reading ({curr_read}) is less than previous reading ({prev_read})")
                    consumption_val = curr_read - prev_read
                    reading_type = 'cumulative'
                except InvalidOperation:
                    raise ValueError(f"Invalid reading format: current='{row[curr_reading_idx]}', prev='{row[prev_reading_idx]}'")
            
            # Scenario B: Direct Consumption column is present
            elif consumption_idx is not None and consumption_idx < len(row) and row[consumption_idx].strip():
                try:
                    consumption_val = Decimal(row[consumption_idx].strip())
                    if consumption_val < 0:
                        raise ValueError(f"Consumption cannot be negative: '{row[consumption_idx]}'")
                    reading_type = 'direct_consumption'
                except InvalidOperation:
                    raise ValueError(f"Invalid consumption format: '{row[consumption_idx]}'")
            
            # Scenario C: Cumulative current reading only, need to search database for last reading
            elif curr_reading_idx is not None and curr_reading_idx < len(row) and row[curr_reading_idx].strip():
                try:
                    curr_read = Decimal(row[curr_reading_idx].strip())
                except InvalidOperation:
                    raise ValueError(f"Invalid current reading format: '{row[curr_reading_idx]}'")
                
                # Look up last APPROVED or PENDING_REVIEW ActivityRecord in database for this Tenant + Meter ID
                last_record = ActivityRecord.objects.filter(
                    tenant=batch.data_source.tenant,
                    source_type='UTILITY',
                    raw_data__meter_id=meter_id
                ).order_by('-period_end').first()
                
                if last_record and 'current_reading' in last_record.raw_data:
                    try:
                        prev_read = Decimal(last_record.raw_data['current_reading'])
                        if curr_read < prev_read:
                            consumption_val = Decimal('0.0')
                            reading_type = 'cumulative_rollover'
                            flag_reason = f"Meter rollover detected? Current reading ({curr_read}) is lower than previous database reading ({prev_read})"
                        else:
                            consumption_val = curr_read - prev_read
                            reading_type = 'cumulative'
                    except (InvalidOperation, KeyError, TypeError):
                        pass
                
                if consumption_val is None:
                    consumption_val = Decimal('0.0')
                    reading_type = 'cumulative_missing_baseline'

            if consumption_val is None:
                raise ValueError("Could not determine consumption value from row data")

            # Normalization to kWh
            unit_multiplier = {
                'KWH': Decimal('1.0'),
                'MWH': Decimal('1000.0'),
                'KVAH': Decimal('0.9')
            }
            multiplier = unit_multiplier[unit_original]
            activity_value = consumption_val * multiplier
            activity_unit = 'kWh'

            # Scope classification
            scope = classify_scope('UTILITY', 'electricity')

            # Populate metadata
            raw_row_dict['meter_id'] = meter_id
            raw_row_dict['facility_name'] = facility_name
            raw_row_dict['reading_type'] = reading_type
            if curr_reading_idx is not None and curr_reading_idx < len(row) and row[curr_reading_idx].strip():
                raw_row_dict['current_reading'] = row[curr_reading_idx].strip()
            if prev_reading_idx is not None and prev_reading_idx < len(row) and row[prev_reading_idx].strip():
                raw_row_dict['previous_reading'] = row[prev_reading_idx].strip()

            status = 'PENDING_REVIEW'
            flag_reason = None
            
            if reading_type == 'cumulative_missing_baseline':
                status = 'FLAGGED'
                flag_reason = f"Missing previous reading for cumulative meter ID '{meter_id}'. Consumption set to 0.0, needs manual adjustment."
            elif reading_type == 'cumulative_rollover' or ('curr_read' in locals() and 'prev_read' in locals() and curr_read < prev_read):
                status = 'FLAGGED'
                flag_reason = f"Meter rollover or data entry error: Current reading ({row[curr_reading_idx].strip()}) is less than previous reading."

            rec = ActivityRecord(
                tenant=batch.data_source.tenant,
                batch=batch,
                source_type='UTILITY',
                scope=scope,
                category='electricity',
                activity_value=activity_value,
                activity_unit=activity_unit,
                activity_value_original=consumption_val,
                activity_unit_original=unit_original,
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
