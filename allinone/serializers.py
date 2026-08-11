from rest_framework import serializers
from .models import skills, parents, learningsupportassitant, booking, payments

class skillsSerializer(serializers.ModelSerializer):
    class Meta:
        model = skills
        fields = '__all__'

class parentsSerializer(serializers.ModelSerializer):   
    class Meta:
        model = parents
        fields = '__all__'      

class learningsupportassitantSerializer(serializers.ModelSerializer):
    class Meta:
        model = learningsupportassitant
        fields = '__all__'  

class bookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = booking
        fields = '__all__'

    # ✅ Outside class Meta, at the same indentation as class Meta
    def validate(self, data):
        lsa = data.get('lsa')
        starttime = data.get('starttime')
        endtime = data.get('endtime')

        if starttime >= endtime:
            raise serializers.ValidationError("Start time must be before end time.")

        overlapping_bookings = booking.objects.filter(
            lsa=lsa,
            starttime__lt=endtime,   # ✅ correct field name + correct logic
            endtime__gt=starttime    # ✅ correct field name + correct logic
        )

        if overlapping_bookings.exists():
            raise serializers.ValidationError(
                "The selected LSA is already booked for this time slot."
            )

        return data   # ✅ return data, NOT data.save()
