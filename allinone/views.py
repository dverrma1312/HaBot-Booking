import logging
import requests
from django.shortcuts import render
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


# Alias for backward compatibility
bookingsviewset = BookingViewSet


# ─── 2. LSA SEARCH ENDPOINT (GET /api/v1/lsas/search/) ────────────
@api_view(['GET'])
def get_lsa(request):
    """
    Optimized LSA search endpoint resolving N+1 query problem using prefetch_related('skills').
    Supports filtering by skill name or username via query parameters.
    """
    username = request.query_params.get('username')
    skill_name = request.query_params.get('skill') or request.query_params.get('skills')

    # Filter by Username
    if username:
        lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(username=username)
        if lsas.exists():
            serializer = LearningSupportAssistantSerializer(lsas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": "No LSA found with that username."}, status=status.HTTP_404_NOT_FOUND)

    # Filter by Skill Name
    if skill_name:
        lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(
            skills__skill_name__icontains=skill_name,
            is_active=True
        ).distinct()
        if lsas.exists():
            serializer = LearningSupportAssistantSerializer(lsas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": f"No LSAs found with skill '{skill_name}'."}, status=status.HTTP_404_NOT_FOUND)

    # Default: Return all active LSAs (Prefetched to eliminate N+1 queries)
    lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(is_active=True)
    serializer = LearningSupportAssistantSerializer(lsas, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Alias function name
lsa_search = get_lsa


# ─── 3. THIRD-PARTY MOCK PAYMENT INITIATION ───────────────────────
@api_view(['POST'])
def initiate_payment(request):
    """
    Mock external service integration using Python 'requests' with exception handling & logging.
    Initiates payment and creates a PENDING payment record.
    """
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')

    if not booking_id or not amount:
        return Response({"error": "booking_id and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        booking_obj = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

    # Integrate external mock payment gateway using Python requests
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

    # Create or update Payment record
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
    """
    Automated webhook endpoint listening to payment success/failure events.
    Dynamically transitions Payment and Booking states.
    """
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