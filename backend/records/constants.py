# constants.py
import math

# SAP Material to Activity Category mapping
# Standard: MAT001-MAT006 are fuels (Scope 1). MAT101-MAT120 are procurement goods/services (Scope 3).
SAP_MATERIALS = {
    'MAT001': {'category': 'fuel_combustion', 'name': 'Diesel Fuel', 'default_unit': 'L'},
    'MAT002': {'category': 'fuel_combustion', 'name': 'Petrol Fuel', 'default_unit': 'L'},
    'MAT003': {'category': 'fuel_combustion', 'name': 'Natural Gas', 'default_unit': 'M3'},
    'MAT004': {'category': 'fuel_combustion', 'name': 'Heating Oil', 'default_unit': 'L'},
    'MAT005': {'category': 'fuel_combustion', 'name': 'Liquefied Petroleum Gas (LPG)', 'default_unit': 'KG'},
    'MAT006': {'category': 'fuel_combustion', 'name': 'Coal', 'default_unit': 'TO'},
    
    'MAT101': {'category': 'procurement', 'name': 'Structural Steel', 'default_unit': 'KG'},
    'MAT102': {'category': 'procurement', 'name': 'Aluminum Sheets', 'default_unit': 'KG'},
    'MAT103': {'category': 'procurement', 'name': 'Cement Mix', 'default_unit': 'TO'},
    'MAT104': {'category': 'procurement', 'name': 'Cardboard Packaging', 'default_unit': 'KG'},
    'MAT105': {'category': 'procurement', 'name': 'Office Paper', 'default_unit': 'KG'},
    'MAT106': {'category': 'procurement', 'name': 'IT Equipment Laptops', 'default_unit': 'KG'},
    'MAT107': {'category': 'procurement', 'name': 'Office Furniture', 'default_unit': 'KG'},
    'MAT108': {'category': 'procurement', 'name': 'Plastic Resins', 'default_unit': 'KG'},
    'MAT109': {'category': 'procurement', 'name': 'Industrial Chemicals', 'default_unit': 'KG'},
    'MAT110': {'category': 'procurement', 'name': 'Copper Wires', 'default_unit': 'KG'},
    'MAT111': {'category': 'procurement', 'name': 'Glass Sheets', 'default_unit': 'KG'},
    'MAT112': {'category': 'procurement', 'name': 'Machinery Lubricants', 'default_unit': 'L'},
    'MAT113': {'category': 'procurement', 'name': 'Cardboard Boxes', 'default_unit': 'KG'},
    'MAT114': {'category': 'procurement', 'name': 'Purchased Water', 'default_unit': 'M3'},
    'MAT115': {'category': 'procurement', 'name': 'Safety Gear / Clothing', 'default_unit': 'KG'},
    'MAT116': {'category': 'procurement', 'name': 'Cleaning Chemical Agents', 'default_unit': 'L'},
    'MAT117': {'category': 'procurement', 'name': 'Stationery Office Supplies', 'default_unit': 'KG'},
    'MAT118': {'category': 'procurement', 'name': 'Textile Canvas Products', 'default_unit': 'KG'},
    'MAT119': {'category': 'procurement', 'name': 'Rubber Seals and Gaskets', 'default_unit': 'KG'},
    'MAT120': {'category': 'procurement', 'name': 'Wooden Pallets', 'default_unit': 'TO'},
}

# Plant/Werks Lookup to Facility Name
PLANT_MAPPING = {
    '1000': 'Munich HQ & R&D Center',
    '2000': 'Hamburg Manufacturing Facility',
    '3000': 'Stuttgart Assembly & Logistics Warehouse',
    '4000': 'Frankfurt Corporate Office',
    '5000': 'Berlin Tech Hub',
    'US01': 'New York Sales Office',
    'US02': 'Austin Data Center',
    'SG01': 'Singapore Logistics Center',
}

# Site text identifier mapping for utility records
UTILITY_SITE_MAPPING = {
    'Munich': 'Munich HQ & R&D Center',
    'Munich HQ': 'Munich HQ & R&D Center',
    'Hamburg': 'Hamburg Manufacturing Facility',
    'Hamburg Plant': 'Hamburg Manufacturing Facility',
    'Stuttgart': 'Stuttgart Assembly & Logistics Warehouse',
    'Stuttgart Warehouse': 'Stuttgart Assembly & Logistics Warehouse',
    'Frankfurt': 'Frankfurt Corporate Office',
    'Berlin': 'Berlin Tech Hub',
    'New York': 'New York Sales Office',
    'Austin': 'Austin Data Center',
    'Singapore': 'Singapore Logistics Center',
}

# Top 50 major airports coordinates (latitude, longitude)
AIRPORT_COORDINATES = {
    'ATL': (33.6407, -84.4277),
    'LAX': (33.9416, -118.4085),
    'ORD': (41.9742, -87.9073),
    'LHR': (51.4700, -0.4543),
    'HND': (35.5494, 139.7798),
    'CDG': (49.0097, 2.5479),
    'FRA': (50.0379, 8.5622),
    'SIN': (1.3644, 103.9915),
    'DXB': (25.2532, 55.3657),
    'JFK': (40.6413, -73.7781),
    'BOM': (19.0896, 72.8656),
    'DEL': (28.5562, 77.1000),
    'AMS': (52.3086, 4.7639),
    'DFW': (32.8998, -97.0403),
    'DEN': (39.8561, -104.6737),
    'SFO': (37.6213, -122.3790),
    'SEA': (47.4502, -122.3088),
    'ICN': (37.4602, 126.4407),
    'SYD': (-33.9461, 151.1772),
    'PEK': (40.0799, 116.5971),
    'CAN': (23.3959, 113.2988),
    'PVG': (31.1443, 121.8083),
    'HKG': (22.3080, 113.9185),
    'BKK': (13.6900, 100.7501),
    'KUL': (2.7456, 101.7072),
    'CGK': (-6.1256, 106.6558),
    'MEL': (-37.6690, 144.8410),
    'AKL': (-37.0081, 174.7917),
    'NRT': (35.7720, 140.3929),
    'MAD': (40.4719, -3.5640),
    'BCN': (41.2974, 2.0833),
    'FCO': (41.8003, 12.2389),
    'MUC': (48.3538, 11.7861),
    'ZRH': (47.4581, 8.5481),
    'CPH': (55.6180, 12.6560),
    'ARN': (59.6519, 17.9186),
    'OSL': (60.1975, 11.1004),
    'HEL': (60.3172, 24.9633),
    'DUB': (53.4264, -6.2699),
    'EDI': (55.9508, -3.3615),
    'MAN': (53.3588, -2.2749),
    'LGW': (51.1537, -0.1821),
    'EWR': (40.6925, -74.1686),
    'MIA': (25.7959, -80.2870),
    'SJC': (37.3626, -121.9290),
    'BOS': (42.3656, -71.0096),
    'YYZ': (43.6777, -79.6248),
    'YVR': (49.1967, -123.1815),
    'MEX': (19.4361, -99.0719),
    'GRU': (-23.4356, -46.4731)
}

def calculate_haversine_distance(origin_code, dest_code):
    """
    Calculate the great-circle distance between two airports in kilometers.
    Returns None if any airport code is missing or not in lookup.
    """
    if not origin_code or not dest_code:
        return None
        
    origin_code = origin_code.strip().upper()
    dest_code = dest_code.strip().upper()
    
    if origin_code not in AIRPORT_COORDINATES or dest_code not in AIRPORT_COORDINATES:
        return None
        
    lat1, lon1 = AIRPORT_COORDINATES[origin_code]
    lat2, lon2 = AIRPORT_COORDINATES[dest_code]
    
    # Haversine formula
    r_earth = 6371.0 # radius of Earth in km
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return round(r_earth * c, 2)


def classify_scope(source_type, category):
    """
    Scope Classification Logic:
    - SAP + material is a fuel type (fuel_combustion) -> SCOPE_1
    - SAP + material is a purchased good/service (procurement) -> SCOPE_3
    - UTILITY electricity -> SCOPE_2
    - TRAVEL flights/hotels/ground -> SCOPE_3
    """
    source_type = source_type.upper()
    if source_type == 'SAP':
        if category == 'fuel_combustion':
            return 'SCOPE_1'
        elif category == 'procurement':
            return 'SCOPE_3'
    elif source_type == 'UTILITY':
        return 'SCOPE_2'
    elif source_type == 'TRAVEL':
        return 'SCOPE_3'
        
    # Default fallback
    return 'SCOPE_3'
