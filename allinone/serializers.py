from rest_framework import serializers
from .models import Skill, Parent, LearningSupportAssistant, Booking, Payment


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = '__all__'


class LearningSupportAssistantSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        source='skills',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = LearningSupportAssistant
        fields = ['id', 'username', 'email', 'phone', 'rate', 'is_active', 'skills', 'skill_ids', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    # Allow sending parent email as primary key or lookup
    parent = serializers.SlugRelatedField(
        slug_field='parent_email',
        queryset=Parent.objects.all()
    )

    class Meta:
        model = Booking
        fields = '__all__'

    def validate(self, data):
        lsa = data.get('lsa')
        starttime = data.get('starttime')
        endtime = data.get('endtime')

        if starttime and endtime and starttime >= endtime:
            raise serializers.ValidationError({"detail": "Start time must be strictly before end time."})

        # Overlap Validation Rule:
        # Existing booking overlaps with requested slot if:
        # DB starttime < requested endtime AND DB endtime > requested starttime
        if lsa and starttime and endtime:
            overlapping_query = Booking.objects.filter(
                lsa=lsa,
                status__in=['PENDING_PAYMENT', 'CONFIRMED'],
                starttime__lt=endtime,
                endtime__gt=starttime
            )

            # If updating an existing booking, exclude itself from overlap check
            if self.instance:
                overlapping_query = overlapping_query.exclude(pk=self.instance.pk)

            if overlapping_query.exists():
                raise serializers.ValidationError(
                    {"detail": "The selected LSA is already booked for the specified time slot."}
                )

        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


# Alias exports for backwards compatibility
skillsSerializer = SkillSerializer
parentsSerializer = ParentSerializer
learningsupportassitantSerializer = LearningSupportAssistantSerializer
bookingSerializer = BookingSerializer
paymentsSerializer = PaymentSerializer
