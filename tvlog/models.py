from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
# Create your models here.
class Show(models.Model):
    name = models.CharField(max_length=100)
    startdate = models.DateField()
    enddate = models.DateField(blank=True, null=True)
    boxart = models.ImageField(blank=True, null=True, upload_to="images/")
    abbreviation = models.CharField(max_length=25, unique=True)
    creation_date = models.DateField(auto_now_add=True,)

    def __str__(self):
        return self.name

class Season(models.Model):
    name = models.CharField(max_length=50) # Seasons could have weird names. Even if most shows will just be a number, having support for something like "specials" would be valuable.
    episodes = models.PositiveSmallIntegerField()
    show = models.ForeignKey("Show", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.show.name} - Season {self.name} ({self.episodes})"

class CurrentlyWatching(models.Model):
    author = models.ForeignKey("auth.user", on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True,)
    season = models.ForeignKey("Season", on_delete=models.CASCADE)
    episode = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.author.username} watching {str(self.season)} on episode {self.episode}"

class Watched(models.Model):
    author = models.ForeignKey("auth.user", on_delete=models.CASCADE)
    show = models.ForeignKey("Show", on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True,)
    rating = models.IntegerField(default=5, validators=[MaxValueValidator(10), MinValueValidator(1)])
    review = models.CharField(max_length=500)
    rewatch = models.BooleanField(default=False)