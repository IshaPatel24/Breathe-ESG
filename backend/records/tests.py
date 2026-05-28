import hashlib
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from records.models import Tenant, DataSource, IngestionBatch, ActivityRecord, IngestionError, AuditLog
from records.constants import (
    calculate_haversine_distance, classify_scope, SAP_MATERIALS, PLANT_MAPPING
)
from ingestion.parsers.sap_parser import parse_sap_file, clean_german_decimal
from ingestion.parsers.utility_parser import parse_utility_file
from ingestion.parsers.travel_parser import parse_travel_file, hash_employee_id

class ESGConstantsAndHelpersTest(TestCase):
    def test_haversine_distance(self):
        dist = calculate_haversine_distance('LHR', 'JFK')
        self.assertIsNotNone(dist)
        self.assertTrue(5500 < dist < 5650, f"Distance LHR-JFK was {dist} km")

        dist_none = calculate_haversine_distance('LHR', 'XYZ')
        self.assertIsNone(dist_none)

    def test_classify_scope(self):
        self.assertEqual(classify_scope('SAP', 'fuel_combustion'), 'SCOPE_1')
        self.assertEqual(classify_scope('SAP', 'procurement'), 'SCOPE_3')
        self.assertEqual(classify_scope('UTILITY', 'electricity'), 'SCOPE_2')
        self.assertEqual(classify_scope('TRAVEL', 'flight'), 'SCOPE_3')

    def test_clean_german_decimal(self):
        self.assertEqual(clean_german_decimal('1.234,56'), Decimal('1234.56'))
        self.assertEqual(clean_german_decimal('1234,56'), Decimal('1234.56'))
        self.assertEqual(clean_german_decimal('100'), Decimal('100.0'))
        self.assertEqual(clean_german_decimal(''), Decimal('0.0'))


class ParserIngestionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        self.user = User.objects.create_user(username="testanalyst", password="password")
        
        self.sap_ds = DataSource.objects.create(
            tenant=self.tenant, source_type="SAP", label="SAP Source"
        )
        self.utility_ds = DataSource.objects.create(
            tenant=self.tenant, source_type="UTILITY", label="Utility Source"
        )
        self.travel_ds = DataSource.objects.create(
            tenant=self.tenant, source_type="TRAVEL", label="Travel Source"
        )

    def test_sap_parser_good_and_bad_rows(self):
        csv_data = (
            "Belnr,Matnr,Werks,Menge,Meins,Datum,Kostl\n"
            "DOC001,MAT001,1000,\"1.200,50\",L,15.01.2026,CC_101\n"
            "DOC002,MAT101,2000,\"500,00\",KG,16.01.2026,CC_102\n"
            "DOC003,MAT001,1000,200,L,2026-01-17,CC_101\n"
            "DOC004,MAT001,1000,200,TONS,18.01.2026,CC_101\n"
        )
        
        batch = IngestionBatch.objects.create(
            data_source=self.sap_ds, uploaded_by=self.user, file_name="sap.csv"
        )
        
        records, errors = parse_sap_file(batch, csv_data.encode('utf-8'))
        if records:
            ActivityRecord.objects.bulk_create(records)
        if errors:
            IngestionError.objects.bulk_create(errors)
        batch.row_count = len(records) + len(errors)
        batch.error_count = len(errors)
        batch.status = 'DONE' if len(errors) < batch.row_count else 'FAILED'
        batch.save()
        
        self.assertEqual(batch.status, 'DONE')
        self.assertEqual(batch.row_count, 4)
        self.assertEqual(batch.error_count, 2)
        
        recs = ActivityRecord.objects.filter(batch=batch)
        self.assertEqual(recs.count(), 2)
        
        rec1 = recs.get(raw_data__document_number="DOC001")
        self.assertEqual(rec1.scope, 'SCOPE_1')
        self.assertEqual(rec1.category, 'fuel_combustion')
        self.assertEqual(rec1.activity_value, Decimal('1200.5000'))
        self.assertEqual(rec1.activity_unit, 'L')
        self.assertEqual(rec1.facility_code, '1000')
        
        rec2 = recs.get(raw_data__document_number="DOC002")
        self.assertEqual(rec2.scope, 'SCOPE_3')
        self.assertEqual(rec2.category, 'procurement')
        self.assertEqual(rec2.activity_value, Decimal('500.0000'))
        self.assertEqual(rec2.activity_unit, 'kg')
        self.assertEqual(rec2.facility_code, '2000')

        errs = IngestionError.objects.filter(batch=batch).order_by('row_number')
        self.assertEqual(errs.count(), 2)
        self.assertIn("Invalid date format", errs.first().error_message)

    def test_sap_parser_stores_unmapped_plant(self):
        # Werks 9999 is unmapped in PLANT_MAPPING
        csv_data = (
            "Belnr,Matnr,Werks,Menge,Meins,Datum,Kostl\n"
            "DOC999,MAT001,9999,100,L,15.01.2026,CC_101\n"
        )
        batch = IngestionBatch.objects.create(
            data_source=self.sap_ds, uploaded_by=self.user, file_name="sap_unmapped.csv"
        )
        records, errors = parse_sap_file(batch, csv_data.encode('utf-8'))
        self.assertEqual(len(records), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0].facility_code, '9999')
        self.assertEqual(records[0].raw_data['facility_name'], 'Unknown Plant (9999)')

    def test_utility_parser(self):
        csv_data = (
            "Meter ID,Start Date,End Date,Consumption,Current Reading,Previous Reading,Unit,Site,Tariff\n"
            "MET01,2026-01-01,2026-01-31,1000,,,kWh,Munich HQ,Commercial\n"
            "MET02,2026-01-01,2026-01-31,5,,,MWh,Hamburg Plant,Commercial\n"
            "MET03,2026-01-01,2026-01-31,,25000,20000,kWh,Hamburg Plant,Commercial\n"
        )
        
        batch = IngestionBatch.objects.create(
            data_source=self.utility_ds, uploaded_by=self.user, file_name="utility.csv"
        )
        
        records, errors = parse_utility_file(batch, csv_data.encode('utf-8'))
        if records:
            ActivityRecord.objects.bulk_create(records)
        if errors:
            IngestionError.objects.bulk_create(errors)
        batch.row_count = len(records) + len(errors)
        batch.error_count = len(errors)
        batch.status = 'DONE' if len(errors) < batch.row_count else 'FAILED'
        batch.save()
        
        self.assertEqual(batch.status, 'DONE')
        self.assertEqual(batch.row_count, 3)
        self.assertEqual(batch.error_count, 0)
        
        recs = ActivityRecord.objects.filter(batch=batch)
        self.assertEqual(recs.count(), 3)
        
        rec1 = recs.get(raw_data__meter_id="MET01")
        self.assertEqual(rec1.activity_value, Decimal('1000.0000'))
        self.assertEqual(rec1.activity_unit, 'kWh')
        self.assertEqual(rec1.scope, 'SCOPE_2')
        self.assertEqual(rec1.raw_data['reading_type'], 'direct_consumption')
        
        rec2 = recs.get(raw_data__meter_id="MET02")
        self.assertEqual(rec2.activity_value, Decimal('5000.0000'))
        
        rec3 = recs.get(raw_data__meter_id="MET03")
        self.assertEqual(rec3.activity_value, Decimal('5000.0000'))

    def test_travel_parser(self):
        csv_data = (
            "Trip ID,Category,Origin,Destination,Distance,Distance Unit,Cabin Class,Check-in Date,Check-out Date,Nights,Employee ID,Cost Center\n"
            "T1,Flight,LHR,JFK,5560,km,Economy,2026-02-01,2026-02-01,,EMP01,CC_101\n"
            "T2,Flight,LHR,JFK,,,Economy,2026-02-02,2026-02-02,,EMP01,CC_101\n"
            "T3,Hotel,Munich,Munich,,,Business,2026-02-05,2026-02-10,5,EMP02,CC_101\n"
        )
        
        batch = IngestionBatch.objects.create(
            data_source=self.travel_ds, uploaded_by=self.user, file_name="travel.csv"
        )
        
        records, errors = parse_travel_file(batch, csv_data.encode('utf-8'))
        if records:
            ActivityRecord.objects.bulk_create(records)
        if errors:
            IngestionError.objects.bulk_create(errors)
        batch.row_count = len(records) + len(errors)
        batch.error_count = len(errors)
        batch.status = 'DONE' if len(errors) < batch.row_count else 'FAILED'
        batch.save()
        
        self.assertEqual(batch.status, 'DONE')
        self.assertEqual(batch.row_count, 3)
        self.assertEqual(batch.error_count, 0)
        
        recs = ActivityRecord.objects.filter(batch=batch)
        self.assertEqual(recs.count(), 3)
        
        rec1 = recs.get(raw_data__trip_id="T1")
        self.assertEqual(rec1.raw_data['employee_id'], '[ANONYMIZED]')
        self.assertEqual(rec1.raw_data['employee_id_hash'], hash_employee_id('EMP01'))
        
        rec2 = recs.get(raw_data__trip_id="T2")
        self.assertTrue(rec2.activity_value > 5500)
        self.assertEqual(rec2.status, 'PENDING_REVIEW')
        
        rec3 = recs.get(raw_data__trip_id="T3")
        self.assertEqual(rec3.activity_value, Decimal('5.0000'))
        self.assertEqual(rec3.activity_unit, 'nights')

    def test_audit_log_fires_on_status_change(self):
        # Create a record and verify AuditLog generation
        rec = ActivityRecord.objects.create(
            tenant=self.tenant,
            batch=IngestionBatch.objects.create(data_source=self.sap_ds, file_name="temp.csv"),
            source_type='SAP',
            scope='SCOPE_1',
            category='fuel_combustion',
            activity_value=Decimal('100.0'),
            activity_unit='L',
            activity_value_original=Decimal('100.0'),
            activity_unit_original='L',
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
            facility_code='1000'
        )
        
        # Verify CREATED log
        self.assertEqual(AuditLog.objects.filter(activity_record=rec, action='CREATED').count(), 1)
        
        # Update status and verify APPROVED log
        rec._changed_by = self.user
        rec.status = 'APPROVED'
        rec.is_locked = True
        rec.save()
        
        self.assertEqual(AuditLog.objects.filter(activity_record=rec, action='APPROVED').count(), 1)
        log = AuditLog.objects.filter(activity_record=rec, action='APPROVED').first()
        self.assertEqual(log.changed_by, self.user)
        self.assertEqual(log.before_state['status'], 'PENDING_REVIEW')
        self.assertEqual(log.after_state['status'], 'APPROVED')
