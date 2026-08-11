from urllib import request
from .models import skills, parents, learningsupportassitant, booking, payments
from .serializers import skillsSerializer, parentsSerializer, learningsupportassitantSerializer, bookingSerializer
from rest_framework.decorators import api_view
from rest_framework import viewsets, permissions, response, status

class bookingsviewset(viewsets.ModelViewSet):
    queryset = booking.objects.all()
    serializer_class = bookingSerializer
    def create(self, request, *args, **kwargs):
        serializer = bookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_lsa (request):
    username = request.query_params.get('username')
    skills_name = request.query_params.get('skills')
    if username: 
            lsa = learningsupportassitant.objects.prefetch_related('skills').filter(username =username)
            if lsa.exists():
                serializer = learningsupportassitantSerializer(lsa, many=True)
                return response.Response(serializer.data)
            else:
                return response.Response(status=status.HTTP_404_NOT_FOUND)
    if skills_name:
        lsa = learningsupportassitant.objects.prefetch_related('skills').filter(
            skills__skill_name=skills_name,
            is_active=True
        )
        if lsa.exists():
            serializer = learningsupportassitantSerializer(lsa, many=True)
            return response.Response(serializer.data)
        else:
            return response.Response(status=status.HTTP_404_NOT_FOUND)
    lsa = learningsupportassitant.objects.prefetch_related('skills').filter(is_active=True)
    serializer = learningsupportassitantSerializer(lsa, many=True)
    return response.Response(serializer.data)
            
@api_view(['POST'])
def paymentgateway(request):
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')
    transaction_id = request.data.get('transaction_id')

    try:
        booking_instance = booking.objects.get(id=booking_id)
    except booking.DoesNotExist:
        return response.Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        payment_instance = request.post('payments', JSON={
            'booking': booking_instance.id,
            'amount': amount,
            'transaction_id': transaction_id
        })
        payment_instance.raise_for_status()
        fatwaydata = payment_instance.json()
    except request.exceptions.connectionError:
        return response.Response({'error': 'Payment gateway connection error.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except request.timeout:
        return response.Response({'error': 'Payment gateway timeout.'}, status=status.HTTP_504_GATEWAY_TIMEOUT) 
    
    payment_new = payments.objects.create(
        booking=booking_instance,
        amount=amount,
        transaction_id=transaction_id,
        status='completed'
    )
    return response.Response({'message': 'Payment successful.', 'payment_id': payment_new.id}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def get_payments(request):
    transaction_id = payments.objects.filter(transaction_id=request.data.get('transaction_id')).first()
    if transaction_id:
        transaction_id.status = 'completed'
        transaction_id.save()
        return response.Response({'message': 'Payment status updated to completed.'}, status=status.HTTP_200_OK)
    else:
        return response.Response({'error': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND) 