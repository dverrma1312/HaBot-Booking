from django.db import models

class Skill(models.Model):
    skill_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.skill_name


class Parent(models.Model):
    parent_name = models.CharField(max_length=255)
    parent_email = models.EmailField(unique=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parent_name} ({self.parent_email})"


class LearningSupportAssistant(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    rate = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    skills = models.ManyToManyField(Skill, related_name='lsas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.username} (${self.rate}/hr)"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]

    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='bookings')
    lsa = models.ForeignKey(LearningSupportAssistant, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField(null=True, blank=True)
    booking_time = models.TimeField(null=True, blank=True)
    starttime = models.DateTimeField(db_index=True)
    endtime = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['starttime', 'endtime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Booking #{self.id} - LSA: {self.lsa.username} | Parent: {self.parent.parent_name} [{self.status}]"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.transaction_reference} - ${self.amount} [{self.status}]"


# Alias mappings for backwards compatibility with existing codebase
skills = Skill
parents = Parent
learningsupportassitant = LearningSupportAssistant
booking = Booking
payments = Payment