from django.db import models

# Create your models here.
class Contact(models.Model):
    lib_id=models.CharField(max_length=50)
    name=models.CharField(max_length=50,default=1)
    frequency=models.CharField(max_length=20,blank=1)

    def __str__(self):
        return self.lib_id
