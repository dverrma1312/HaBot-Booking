from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Parent, LearningSupportAssistant, Skill, Booking, Payment


class BookingAPITestCase(APITestCase):

    def setUp(self):
        """
        Runs automatically before EVERY test method.
        Creates clean, isolated test data in the temporary database.
        """
        # 1. Create test skill
        self.skill = Skill.objects.create(skill_name="Autism Support")

        # 2. Create test parent
        self.parent = Parent.objects.create(
            parent_name="John Doe",
            parent_email="john@example.com",
            parent_phone="1234567890"
        )

        # 3. Create test LSA
        self.lsa = LearningSupportAssistant.objects.create(
            username="sarah",
            password="password123",
            email="sarah@example.com",
            phone="1234567890",
            rate=25.00,
            is_active=True
        )
        self.lsa.skills.add(self.skill)

        # 4. Get URL routes by their names
        self.bookings_url = reverse('v1-bookings')
        self.lsa_search_url = reverse('v1-lsa-search')
        self.initiate_url = reverse('v1-payment-initiate')
        self.webhook_url = reverse('v1-payment-webhook')

    # ─── TEST 1: SUCCESSFUL BOOKING CREATION ─────────────────────────
    def test_successful_booking_creation(self):
        payload = {
            "parent": self.parent.parent_email,
            "lsa": self.lsa.id,
            "booking_date": "2026-08-20",
            "booking_time": "10:00:00",
            "starttime": "2026-08-20T10:00:00Z",
            "endtime": "2026-08-20T12:00:00Z"
        }

        response = self.client.post(self.bookings_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Booking.objects.get().lsa, self.lsa)

    # ─── TEST 2: DOUBLE-BOOKING PREVENTION ───────────────────────────
    def test_double_booking_prevention(self):
        # Create an existing booking from 10:00 to 12:00
        Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            booking_date="2026-08-20",
            booking_time="10:00:00",
            starttime="2026-08-20T10:00:00Z",
            endtime="2026-08-20T12:00:00Z",
            status="PENDING_PAYMENT"
        )

        # Try creating an OVERLAPPING booking (11:00 to 13:00)
        overlapping_payload = {
            "parent": self.parent.parent_email,
            "lsa": self.lsa.id,
            "booking_date": "2026-08-20",
            "booking_time": "11:00:00",
            "starttime": "2026-08-20T11:00:00Z",
            "endtime": "2026-08-20T13:00:00Z"
        }
        response = self.client.post(self.bookings_url, overlapping_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertIn("detail", response.data)

    # ─── TEST 3: OPTIMIZED LSA SEARCH BY SKILL ────────────────────────
    def test_lsa_search_by_skill(self):
        url = f"{self.lsa_search_url}?skill=Autism Support"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'sarah')

    # ─── TEST 4: PAYMENT INITIATION ──────────────────────────────────
    def test_payment_initiation(self):
        booking_obj = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            booking_date="2026-08-20",
            booking_time="10:00:00",
            starttime="2026-08-20T10:00:00Z",
            endtime="2026-08-20T12:00:00Z",
            status="PENDING_PAYMENT"
        )

        payload = {
            "booking_id": booking_obj.id,
            "amount": 50.00
        }
        response = self.client.post(self.initiate_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.get().status, 'PENDING')

    # ─── TEST 5: PAYMENT WEBHOOK SUCCESS STATE TRANSITION ─────────────
    def test_payment_webhook_success(self):
        booking_obj = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            booking_date="2026-08-20",
            booking_time="10:00:00",
            starttime="2026-08-20T10:00:00Z",
            endtime="2026-08-20T12:00:00Z",
            status="PENDING_PAYMENT"
        )
        payment_obj = Payment.objects.create(
            booking=booking_obj,
            amount=50.00,
            transaction_reference="TXN_TEST_123",
            status="PENDING"
        )

        payload = {
            "transaction_reference": "TXN_TEST_123",
            "status": "success"
        }
        response = self.client.post(self.webhook_url, payload, format='json')

        payment_obj.refresh_from_db()
        booking_obj.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment_obj.status, "SUCCESSFUL")
        self.assertEqual(booking_obj.status, "CONFIRMED")

    # ─── TEST 6: PAYMENT WEBHOOK FAILURE STATE TRANSITION ─────────────
    def test_payment_webhook_failure(self):
        booking_obj = Booking.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            booking_date="2026-08-20",
            booking_time="10:00:00",
            starttime="2026-08-20T10:00:00Z",
            endtime="2026-08-20T12:00:00Z",
            status="PENDING_PAYMENT"
        )
        payment_obj = Payment.objects.create(
            booking=booking_obj,
            amount=50.00,
            transaction_reference="TXN_TEST_456",
            status="PENDING"
        )

        payload = {
            "transaction_reference": "TXN_TEST_456",
            "status": "failed"
        }
        response = self.client.post(self.webhook_url, payload, format='json')

        payment_obj.refresh_from_db()
        booking_obj.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment_obj.status, "FAILED")
        self.assertEqual(booking_obj.status, "CANCELLED")