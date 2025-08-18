from rest_framework import serializers
from .models import Genre, Movie


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name", "slug")


class MovieSerializer(serializers.ModelSerializer):
    video_1080 = serializers.FileField(read_only=True)
    video_720 = serializers.FileField(read_only=True)
    video_480 = serializers.FileField(read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)
    processing_status = serializers.CharField(read_only=True)

    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "logo",
            "hero_image",
            "thumbnail_image",
            "teaser_video",
            "video_1080",
            "video_720",
            "video_480",
            "duration_seconds",
            "processing_status",
            "is_hero",
            "genre_ids",
            "created_at",
        )
