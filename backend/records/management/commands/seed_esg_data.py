import os
import csv
import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token
from records.models import Tenant, DataSource, IngestionBatch, ActivityRecord, IngestionError
from records.constants import PLANT_MAPPING, UTILITY_SITE_MAPPING, SAP_MATERIALS, AIRPORT_COORDINATES

class Command(BaseCommand):
    help = "Seeds database with default tenant, users, tokens, and generates realistic CSV seed files."

    def handle(self, *args, **options):
        self.stdout.write("Initializing Breathe ESG database seed...")

        # 1. Create Default Tenant
        tenant, created = Tenant.objects.get_or_create(
            slug="breathe-ind",
            defaults={"name": "Breathe Industries Ltd"}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Tenant: {tenant.name}"))
        else:
            self.stdout.write(f"Tenant {tenant.name} already exists.")

        # 2. Create Users & Tokens
        admin_user, admin_created = User.objects.get_or_create(
            username="admin",
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "email": "admin@breatheesg.com"
            }
        )
        if admin_created:
            admin_user.set_password("adminpass")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (password: adminpass)"))
        admin_token, _ = Token.objects.get_or_create(user=admin_user)
        self.stdout.write(f"Admin Token: {admin_token.key}")

        analyst_user, analyst_created = User.objects.get_or_create(
            username="analyst",
            defaults={
                "email": "analyst@breatheesg.com"
            }
        )
        if analyst_created:
            analyst_user.set_password("analystpass")
            analyst_user.save()
            self.stdout.write(self.style.SUCCESS("Created analyst user (password: analystpass)"))
        analyst_token, _ = Token.objects.get_or_create(user=analyst_user)
        self.stdout.write(f"Analyst Token: {analyst_token.key}")

        # 3. Create DataSources
        sap_ds, _ = DataSource.objects.get_or_create(
            tenant=tenant,
            source_type="SAP",
            defaults={"label": "ERP SAP Export"}
        )
        utility_ds, _ = DataSource.objects.get_or_create(
            tenant=tenant,
            source_type="UTILITY",
            defaults={"label": "Utility Electricity Billings"}
        )
        travel_ds, _ = DataSource.objects.get_or_create(
            tenant=tenant,
            source_type="TRAVEL",
            defaults={"label": "Corporate Travel Expenses"}
        )
        self.stdout.write("Provisioned DataSources.")

        # 4. Generate CSV Seed Files on Filesystem
        seed_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "seed_data")
        os.makedirs(seed_dir, exist_ok=True)

        self.generate_sap_csv(seed_dir)
        self.generate_utility_csv(seed_dir)
        self.generate_travel_csv(seed_dir)

        # 5. Populate some initial historical batches and records in database so the UI isn't empty
        self.seed_historical_db_data(tenant, sap_ds, utility_ds, travel_ds, analyst_user)

        self.stdout.write(self.style.SUCCESS("Database seeding and seed file generation complete!"))

    def generate_sap_csv(self, output_dir):
        file_path = os.path.join(output_dir, "sap_seed.csv")
        headers = ["Belnr", "Matnr", "Werks", "Menge", "Meins", "Datum", "Kostl"]
        
        # We need 50 rows
        rows = []
        
        # Normal rows
        plants = list(PLANT_MAPPING.keys())
        materials = list(SAP_MATERIALS.keys())
        
        for i in range(1, 47):
            belnr = f"1000{i:04d}"
            mat = random.choice(materials)
            werks = random.choice(plants)
            
            # Format qty with decimal commas and thousands separator
            qty_raw = round(random.uniform(50, 1500), 2)
            qty_parts = f"{qty_raw:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            unit = SAP_MATERIALS[mat]['default_unit']
            
            # DD.MM.YYYY
            dt = date(2026, 1, 1) + timedelta(days=random.randint(0, 90))
            dt_str = dt.strftime("%d.%m.%Y")
            
            kostl = f"CC_{random.randint(100, 199)}"
            rows.append([belnr, mat, werks, qty_parts, unit, dt_str, kostl])

        # Error rows
        # 1. Bad Date Format
        rows.append(["E0001", "MAT001", "1000", "500,00", "L", "2026-03-15", "CC_101"])
        # 2. Bad Unit original
        rows.append(["E0002", "MAT002", "2000", "125,50", "TONNES", "15.03.2026", "CC_102"])
        # 3. Missing Plant Code
        rows.append(["E0003", "MAT003", "", "1.500,00", "M3", "18.03.2026", "CC_103"])
        # 4. Unknown Material Code
        rows.append(["E0004", "MAT999", "3000", "10,00", "KG", "20.03.2026", "CC_104"])

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"Generated SAP seed CSV at: {file_path}")

    def generate_utility_csv(self, output_dir):
        file_path = os.path.join(output_dir, "utility_seed.csv")
        headers = ["Meter ID", "Start Date", "End Date", "Consumption", "Current Reading", "Previous Reading", "Unit", "Site", "Tariff"]
        
        rows = []
        meters = {
            "MET-MUN-01": "Munich HQ",
            "MET-HAM-02": "Hamburg Plant",
            "MET-AUS-03": "Austin Data Center"
        }
        
        # Let's write 30 rows
        for i in range(1, 26):
            meter = random.choice(list(meters.keys()))
            site = meters[meter]
            
            # Start/End date straddling months
            # E.g. Month i
            start = date(2025, 12, 1) + timedelta(days=(i-1)*30)
            end = start + timedelta(days=29)
            
            # Simple values
            consumption = round(random.uniform(5000, 25000), 2)
            
            unit = "kWh"
            if i % 10 == 0:
                unit = "MWh"
                consumption = round(consumption / 1000, 4)
            elif i % 10 == 5:
                unit = "kVAh"
            
            tariff = f"Standard Commercial {random.choice(['Tier 1', 'Tier 2'])}"
            
            # Write row with direct consumption
            rows.append([meter, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), str(consumption), "", "", unit, site, tariff])

        # Add 5 rows with cumulative readings
        cumulative_meters = ["MET-CUM-01", "MET-CUM-02"]
        current_readings = {
            "MET-CUM-01": Decimal('100000.0'),
            "MET-CUM-02": Decimal('50000.0')
        }
        
        for k in range(5):
            meter = cumulative_meters[k % 2]
            site = "Austin Data Center" if meter == "MET-CUM-02" else "Hamburg Plant"
            start = date(2026, 1, 1) + timedelta(days=k*30)
            end = start + timedelta(days=29)
            
            prev_read = current_readings[meter]
            usage = Decimal(str(random.randint(2000, 8000)))
            curr_read = prev_read + usage
            current_readings[meter] = curr_read # update state for next iteration
            
            rows.append([meter, start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y"), "", str(curr_read), str(prev_read), "kWh", site, "Industrial Time-of-Use"])

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"Generated Utility seed CSV at: {file_path}")

    def generate_travel_csv(self, output_dir):
        file_path = os.path.join(output_dir, "travel_seed.csv")
        headers = ["Trip ID", "Category", "Origin", "Destination", "Distance", "Distance Unit", "Cabin Class", "Check-in Date", "Check-out Date", "Nights", "Employee ID", "Cost Center"]
        
        rows = []
        categories = ["Flight", "Air", "flight", "Hotel", "accommodation", "car rental", "rental", "train", "taxi"]
        airports = list(AIRPORT_COORDINATES.keys())
        
        for i in range(1, 38):
            trip_id = f"TRIP_{1000+i}"
            cat = random.choice(categories)
            emp_id = f"EMP{random.randint(1000, 9999)}"
            cc = f"CC_{random.choice(['MKT', 'ENG', 'SALES', 'OPS'])}"
            
            start_date = date(2026, 1, 1) + timedelta(days=random.randint(0, 100))
            end_date = start_date + timedelta(days=random.randint(1, 7))
            
            origin = "Munich"
            dest = "New York"
            dist = ""
            dist_unit = ""
            cabin = ""
            nights = ""
            
            # Categorize normalized behavior
            # Inconsistent categories testing
            low_cat = cat.lower()
            if 'flight' in low_cat or 'air' in low_cat:
                origin = random.choice(airports)
                dest = random.choice([a for a in airports if a != origin])
                dist = str(round(random.uniform(500, 8000), 2))
                dist_unit = random.choice(["km", "miles", ""])
                cabin = random.choice(["Economy", "Business", "First"])
            elif 'hotel' in low_cat or 'accommodation' in low_cat:
                dest = random.choice(["Munich", "Hamburg", "Austin", "Singapore", "New York"])
                nights = str((end_date - start_date).days)
            else: # Ground
                dist = str(round(random.uniform(10, 300), 2))
                dist_unit = "km"
                dest = "City Pair"

            rows.append([
                trip_id, cat, origin, dest, dist, dist_unit, cabin,
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                nights, emp_id, cc
            ])

        # Error / Flagged rows
        # 1. Flight with missing distance (Origin/Destination are top 50 LHR -> JFK) -> testing great-circle calculations
        rows.append(["TRIP_M01", "Flight", "LHR", "JFK", "", "", "Economy", "2026-04-10", "2026-04-10", "", "EMP4500", "CC_ENG"])
        # 2. Flight with missing distance AND invalid airport code (Origin/Destination: LHR -> XYZ) -> testing flagging
        rows.append(["TRIP_M02", "Flight", "LHR", "XYZ", "", "", "Economy", "2026-04-11", "2026-04-11", "", "EMP4501", "CC_ENG"])
        # 3. Hotel check-in/out reverse dates
        rows.append(["TRIP_E01", "Hotel", "Hamburg", "Hamburg", "", "", "", "2026-04-20", "2026-04-18", "2", "EMP4502", "CC_MKT"])

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"Generated Travel seed CSV at: {file_path}")

    def seed_historical_db_data(self, tenant, sap_ds, utility_ds, travel_ds, analyst_user):
        """
        Seeds the DB with pre-computed records so the UI is active out of the box.
        """
        # Create a historical batch
        batch = IngestionBatch.objects.create(
            data_source=sap_ds,
            uploaded_by=analyst_user,
            file_name="historical_erp_sap.csv",
            status="DONE",
            row_count=10,
            error_count=0,
            notes="Pre-seeded historical data."
        )

        # Seed 10 records
        # 4 SAP (Scope 1 and 3)
        ActivityRecord.objects.create(
            tenant=tenant,
            batch=batch,
            source_type='SAP',
            scope='SCOPE_1',
            category='fuel_combustion',
            activity_value=Decimal('5000.0000'),
            activity_unit='L',
            activity_value_original=Decimal('5000.0000'),
            activity_unit_original='L',
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 1),
            facility_code='1000',
            raw_data={'belnr': 'H0001', 'matnr': 'MAT001', 'werks': '1000', 'menge': '5000', 'meins': 'L'},
            status='APPROVED',
            is_locked=True,
            reviewed_by=analyst_user,
            reviewed_at=timezone.now()
        )

        ActivityRecord.objects.create(
            tenant=tenant,
            batch=batch,
            source_type='SAP',
            scope='SCOPE_1',
            category='fuel_combustion',
            activity_value=Decimal('8200.5000'),
            activity_unit='L',
            activity_value_original=Decimal('8200.5000'),
            activity_unit_original='L',
            period_start=date(2025, 10, 15),
            period_end=date(2025, 10, 15),
            facility_code='2000',
            raw_data={'belnr': 'H0002', 'matnr': 'MAT001', 'werks': '2000', 'menge': '8200,50', 'meins': 'L'},
            status='PENDING_REVIEW',
            is_locked=False
        )

        ActivityRecord.objects.create(
            tenant=tenant,
            batch=batch,
            source_type='SAP',
            scope='SCOPE_3',
            category='procurement',
            activity_value=Decimal('15.5000'),
            activity_unit='tonnes',
            activity_value_original=Decimal('15.5000'),
            activity_unit_original='TO',
            period_start=date(2025, 11, 1),
            period_end=date(2025, 11, 1),
            facility_code='3000',
            raw_data={'belnr': 'H0003', 'matnr': 'MAT103', 'werks': '3000', 'menge': '15,50', 'meins': 'TO'},
            status='PENDING_REVIEW',
            is_locked=False
        )

        # 3 Utilities (Scope 2)
        util_batch = IngestionBatch.objects.create(
            data_source=utility_ds,
            uploaded_by=analyst_user,
            file_name="historical_utility_bills.csv",
            status="DONE",
            row_count=5,
            error_count=0
        )
        
        ActivityRecord.objects.create(
            tenant=tenant,
            batch=util_batch,
            source_type='UTILITY',
            scope='SCOPE_2',
            category='electricity',
            activity_value=Decimal('12000.0000'),
            activity_unit='kWh',
            activity_value_original=Decimal('12000.0000'),
            activity_unit_original='kWh',
            period_start=date(2025, 9, 1),
            period_end=date(2025, 9, 30),
            facility_code='MET-MUN-01',
            raw_data={'meter_id': 'MET-MUN-01', 'site_name': 'Munich HQ'},
            status='APPROVED',
            is_locked=True,
            reviewed_by=analyst_user,
            reviewed_at=timezone.now()
        )

        ActivityRecord.objects.create(
            tenant=tenant,
            batch=util_batch,
            source_type='UTILITY',
            scope='SCOPE_2',
            category='electricity',
            activity_value=Decimal('45000.0000'),  # 45 MWh -> 45000 kWh
            activity_unit='kWh',
            activity_value_original=Decimal('45.0000'),
            activity_unit_original='MWH',
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
            facility_code='MET-HAM-02',
            raw_data={'meter_id': 'MET-HAM-02', 'site_name': 'Hamburg Plant'},
            status='FLAGGED',
            flag_reason='Spike in energy usage detected compared to historical baseline (> 30% increase)',
            is_locked=False
        )

        # 3 Travel (Scope 3)
        travel_batch = IngestionBatch.objects.create(
            data_source=travel_ds,
            uploaded_by=analyst_user,
            file_name="historical_travel_expenses.csv",
            status="DONE",
            row_count=10,
            error_count=0
        )
        
        ActivityRecord.objects.create(
            tenant=tenant,
            batch=travel_batch,
            source_type='TRAVEL',
            scope='SCOPE_3',
            category='flight',
            activity_value=Decimal('5562.0000'), # LHR -> JFK direct calculation fallback
            activity_unit='km',
            activity_value_original=Decimal('5562.0000'),
            activity_unit_original='km',
            period_start=date(2025, 11, 5),
            period_end=date(2025, 11, 5),
            facility_code='LHR-JFK',
            raw_data={'trip_id': 'HT-101', 'category': 'Flight', 'origin': 'LHR', 'destination': 'JFK'},
            status='PENDING_REVIEW',
            is_locked=False
        )

        ActivityRecord.objects.create(
            tenant=tenant,
            batch=travel_batch,
            source_type='TRAVEL',
            scope='SCOPE_3',
            category='hotel',
            activity_value=Decimal('4.0000'),
            activity_unit='nights',
            activity_value_original=Decimal('4.0000'),
            activity_unit_original='nights',
            period_start=date(2025, 11, 5),
            period_end=date(2025, 11, 9),
            facility_code='New York',
            raw_data={'trip_id': 'HT-101', 'category': 'Hotel', 'destination': 'New York'},
            status='APPROVED',
            is_locked=True,
            reviewed_by=analyst_user,
            reviewed_at=timezone.now()
        )
