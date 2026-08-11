from django.db import models

class skills(models.Model):
    skill_name = models.CharField(max_length=100)

    def __str__(self):
        return self.skill_name
class parents(models.Model):
    parent_name = models.CharField(max_length=100)
    parent_email = models.EmailField(primary_key=True)
    parent_phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.parent_name

class learningsupportassitant(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    rate = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    skills = models.ManyToManyField(skills, related_name='lsas')

    class Meta:                                          
        indexes = [models.Index(fields=['is_active'])]  

    def __str__(self):
        return self.username                          

class booking(models.Model):
    parent = models.ForeignKey(parents, on_delete=models.PROTECT)
    lsa = models.ForeignKey(learningsupportassitant, on_delete=models.PROTECT)
    booking_date = models.DateField()
    booking_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], default='pending')

    class meta:
        index = [ models.Index(fields=['starttime, endtime '])]

    def __str__(self):
        return f"Booking by {self.parent.parent_name} with {self.lsa} on {self.booking_date} at {self.booking_time}"

class payments(models.Model):
    booking = models.ForeignKey(booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)

    class meta:
        index = [ models.Index(fields=['transaction_id'])]

    def __str__(self):
        return f"Payment of {self.amount} for booking {self.booking.id}"