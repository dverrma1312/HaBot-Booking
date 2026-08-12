import logging
import requests
from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Skill, Parent, LearningSupportAssistant, Booking, Payment,
    skills, parents, learningsupportassitant, booking, payments
)
from .serializers import (
    SkillSerializer, ParentSerializer, LearningSupportAssistantSerializer,
    BookingSerializer, PaymentSerializer,
    skillsSerializer, parentsSerializer, learningsupportassitantSerializer,
    bookingSerializer, paymentsSerializer
)

logger = logging.getLogger(__name__)


# ─── FRONTEND DASHBOARD VIEW ───────────────────────────────────────
def dashboard_view(request):
    """Renders the interactive showcase UI for testing API endpoints."""
    return render(request, 'dashboard.html')


# ─── 1. BOOKING ENDPOINT (POST /api/v1/bookings/) ─────────────────
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Alias
bookingsviewset = BookingViewSet


# ─── 2. LSA SEARCH ENDPOINT (GET /api/v1/lsas/search/) ────────────
@api_view(['GET'])
def get_lsa(request):
    """
    LSA search endpoint resolving N+1 query problem using prefetch_related('skills').
    Supports searching by skill name or username.
    """
    search_term = (
        request.query_params.get('skill') or 
        request.query_params.get('query') or 
        request.query_params.get('skills') or 
        request.query_params.get('username')
    )

    if search_term:
        search_term = str(search_term).strip()
        lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(
            Q(skills__skill_name__icontains=search_term) | Q(username__icontains=search_term),
            is_active=True
        ).distinct()
        
        if lsas.exists():
            serializer = LearningSupportAssistantSerializer(lsas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": f"No active LSAs found for '{search_term}'."}, status=status.HTTP_404_NOT_FOUND)

    # Default: Return all active LSAs (Prefetched to eliminate N+1 queries)
    lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(is_active=True)
    serializer = LearningSupportAssistantSerializer(lsas, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Alias
lsa_search = get_lsa


# ─── SEED SAMPLE DATA HELPER (POST /api/v1/seed/) ─────────────────
@api_view(['POST'])
def seed_data(request):
    """Seeds test data into SQLite database for quick testing."""
    s1, _ = Skill.objects.get_or_create(skill_name='Autism Support')
    s2, _ = Skill.objects.get_or_create(skill_name='Speech Therapy')
    s3, _ = Skill.objects.get_or_create(skill_name='ADHD Management')
    s4, _ = Skill.objects.get_or_create(skill_name='Dyslexia Assistance')

    p1, _ = Parent.objects.get_or_create(parent_email='john@example.com', defaults={'parent_name': 'John Doe', 'parent_phone': '1234567890'})
    p2, _ = Parent.objects.get_or_create(parent_email='alice@example.com', defaults={'parent_name': 'Alice Smith', 'parent_phone': '9876543210'})

    l1, _ = LearningSupportAssistant.objects.get_or_create(username='sarah', defaults={'email': 'sarah@example.com', 'rate': 25.00, 'is_active': True})
    l1.skills.add(s1, s2)

    l2, _ = LearningSupportAssistant.objects.get_or_create(username='david', defaults={'email': 'david@example.com', 'rate': 30.00, 'is_active': True})
    l2.skills.add(s1, s3)

    l3, _ = LearningSupportAssistant.objects.get_or_create(username='emily', defaults={'email': 'emily@example.com', 'rate': 28.00, 'is_active': True})
    l3.skills.add(s2, s4)

    return Response({
        "message": "Sample database data seeded successfully!",
        "parents_count": Parent.objects.count(),
        "lsas_count": LearningSupportAssistant.objects.count(),
        "skills_count": Skill.objects.count()
    }, status=status.HTTP_200_OK)


# ─── 3. THIRD-PARTY MOCK PAYMENT INITIATION ───────────────────────
@api_view(['POST'])
def initiate_payment(request):
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')

    if not booking_id or not amount:
        return Response({"error": "booking_id and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        booking_obj = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

    transaction_ref = f"TXN_{booking_id}_MOCK"
    try:
        mock_response = requests.post(
            'https://mockpaymentgateway.example.com/pay',
            json={
                "amount": float(amount),
                "booking_id": booking_id,
                "callback_url": "http://127.0.0.1:8000/api/v1/payments/webhook/"
            },
            timeout=5
        )
        mock_response.raise_for_status()
        gateway_data = mock_response.json()
        transaction_ref = gateway_data.get('transaction_reference', transaction_ref)

    except requests.exceptions.ConnectionError:
        logger.error("Payment gateway connection error — using fallback mock transaction reference.")
    except requests.exceptions.Timeout:
        logger.error("Payment gateway request timed out — using fallback mock transaction reference.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Payment gateway error: {e} — using fallback mock transaction reference.")

    payment_obj, created = Payment.objects.get_or_create(
        booking=booking_obj,
        defaults={
            'amount': amount,
            'transaction_reference': transaction_ref,
            'status': 'PENDING'
        }
    )

    if not created:
        payment_obj.transaction_reference = transaction_ref
        payment_obj.amount = amount
        payment_obj.status = 'PENDING'
        payment_obj.save()

    return Response({
        "message": "Payment initiated successfully.",
        "transaction_reference": payment_obj.transaction_reference,
        "payment": PaymentSerializer(payment_obj).data
    }, status=status.HTTP_201_CREATED)


# Alias
paymentgateway = initiate_payment


# ─── 4. AUTOMATED PAYMENT WEBHOOK ENDPOINT ───────────────────────
@api_view(['POST'])
def payment_webhook(request):
    transaction_ref = request.data.get('transaction_reference') or request.data.get('transaction_id')
    event_status = request.data.get('status')

    if not transaction_ref or not event_status:
        return Response(
            {"error": "transaction_reference and status are required in payload."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        payment_obj = Payment.objects.get(transaction_reference=transaction_ref)
    except Payment.DoesNotExist:
        return Response({"error": "Payment record with provided reference not found."}, status=status.HTTP_404_NOT_FOUND)

    event_status_lower = str(event_status).lower()

    if event_status_lower in ['success', 'successful', 'completed', 'paid']:
        payment_obj.status = 'SUCCESSFUL'
        payment_obj.booking.status = 'CONFIRMED'
    elif event_status_lower in ['failed', 'failure', 'cancelled', 'declined']:
        payment_obj.status = 'FAILED'
        payment_obj.booking.status = 'CANCELLED'
    else:
        return Response({"error": f"Invalid status '{event_status}'."}, status=status.HTTP_400_BAD_REQUEST)

    payment_obj.save()
    payment_obj.booking.save()

    return Response({
        "message": "Webhook processed successfully.",
        "payment_status": payment_obj.status,
        "booking_status": payment_obj.booking.status,
        "payment": PaymentSerializer(payment_obj).data,
        "booking": BookingSerializer(payment_obj.booking).data
    }, status=status.HTTP_200_OK)