from rest_framework import serializers
from django.urls import reverse
from django.conf import settings
from urllib.parse import urljoin
from .models import Favorite, Genre, Movie


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for Genre model. Returns id, name, and slug."""
    class Meta:
        model = Genre
        fields = ("id", "name", "slug")


class MovieSerializer(serializers.ModelSerializer):
    """Serializer for Movie model. Includes basic fields, file URLs (logo, hero image, thumbnail, teaser, videos), duration, status, and favorite info."""
    logo = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()
    thumbnail_image = serializers.SerializerMethodField()
    teaser_video = serializers.SerializerMethodField()
    video_1080 = serializers.FileField(read_only=True)
    video_720 = serializers.FileField(read_only=True)
    video_480 = serializers.FileField(read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)
    processing_status = serializers.CharField(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    def _has_file(self, f):
        return bool(f and getattr(f, "name", None))

    def _abs(self, request, name: str, pk: int) -> str:
        rel = reverse(name, args=[pk])
        base = getattr(settings, "SITE_BASE_URL", None)
        if base:
            return urljoin(base, rel)
        return request.build_absolute_uri(rel) if request is not None else rel

    def get_logo(self, obj):
        request = self.context.get("request")
        return self._abs(request, "logo", obj.pk) if self._has_file(getattr(obj, "logo", None)) else None

    def get_hero_image(self, obj):
        request = self.context.get("request")
        return self._abs(request, "hero-image", obj.pk) if self._has_file(getattr(obj, "hero_image", None)) else None

    def get_thumbnail_image(self, obj):
        request = self.context.get("request")
        return (
            self._abs(request, "thumbnail", obj.pk) if self._has_file(getattr(obj, "thumbnail_image", None)) else None
        )

    def get_teaser_video(self, obj):
        request = self.context.get("request")
        return (
            self._abs(request, "teaser-stream", obj.pk) if self._has_file(getattr(obj, "teaser_video", None)) else None
        )

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
            "genres",
            "created_at",
            "is_favorite",
        )

    def get_is_favorite(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        # for the Performance: view kann pass a  set[int]
        fav_ids = self.context.get("favorite_ids")
        if fav_ids is not None:
            return obj.id in fav_ids

        # Fallback (one more request in the db
        return Favorite.objects.filter(user=user, movie_id=obj.id).exists()
