from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date
# Create your models here.
class Show(models.Model):
    name = models.CharField(max_length=100)
    startdate = models.DateField()
    enddate = models.DateField(blank=True, null=True)
    boxart = models.ImageField(blank=True, null=True, upload_to="images/")
    abbreviation = models.SlugField()
    creation_date = models.DateField(auto_now_add=True,)

    def __str__(self):
        return self.name

class Season(models.Model):
    name = models.CharField(max_length=50) # Seasons could have weird names. Even if most shows will just be a number, having support for something like "specials" would be valuable.
    episodes = models.PositiveSmallIntegerField()
    show = models.ForeignKey("Show", on_delete=models.CASCADE)
    startdate = models.DateField()

    def __str__(self):
        return f"{self.show.name} - Season {self.name} ({self.episodes})"

class CurrentlyWatching(models.Model):
    author = models.ForeignKey("auth.user", on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    season = models.ForeignKey("Season", on_delete=models.CASCADE)
    episode = models.PositiveSmallIntegerField(default=1)
    rating = models.IntegerField(default=0, validators=[MaxValueValidator(10), MinValueValidator(0)]) # 0 = No rating.
    rewatch = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.author.username} watching {str(self.season)} on episode {self.episode}"

    def clean(self):
        if self.episode > self.season.episodes:
            raise ValidationError({'episode': _(f"Episode may not exceed {self.season.episodes}.")})

        if self.episode < 0:
            raise ValidationError({'episode': _("Episode cannot be lower than zero.")})

class UserEx(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    isEditor = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
