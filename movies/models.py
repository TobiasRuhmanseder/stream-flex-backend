from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    logo = models.ImageField(upload_to="movies/logos/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="movies/hero_images/", blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to="movies/thumbnails/", blank=True, null=True)
    teaser_video = models.FileField(upload_to="movies/teasers/", blank=True, null=True)
    video_file = models.FileField(upload_to="movies/videos/", blank=True, null=True)
    video_1080 = models.FileField(upload_to="movies/variants/", blank=True, null=True)
    video_720 = models.FileField(upload_to="movies/variants/", blank=True, null=True)
    video_480 = models.FileField(upload_to="movies/variants/", blank=True, null=True)
    is_hero = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    PROCESSING_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]
    processing_status = models.CharField(max_length=12, choices=PROCESSING_CHOICES, default="pending")
    processing_error = models.TextField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.title
