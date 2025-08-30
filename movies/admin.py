from django.contrib import admin
from django.db.models import Count
from .models import Favorite, Genre, Movie

READONLY_ASSETS = ("teaser_video", "thumbnail_image",
                   "video_1080", "video_720", "video_480")


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # FK: wir können das Genre direkt anzeigen
    list_display = ("id", "title", "genre_display", "is_hero", "created_at")
    list_filter = ("is_hero", "created_at")
    search_fields = ("title", "description")
    readonly_fields = READONLY_ASSETS

    fieldsets = (
        (None, {
            "fields": ("title", "description", "genre", "is_hero"),
        }),
        ("Assets (vom RQ-Worker gefüllt)", {
            "fields": READONLY_ASSETS,
            "description": "Diese Felder sind schreibgeschützt und werden asynchron generiert.",
        }),
    )

    def get_queryset(self, request):

        qs = super().get_queryset(request)
        return qs.select_related("genre")

    @admin.display(description="Genre")
    def genre_display(self, obj):
        return obj.genre.name if obj.genre_id else "—"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "movie_count", "created_at")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # neues related_name aus deinem FK (oder "movie_set", falls du keines gesetzt hast)
        return qs.annotate(_movie_count=Count("movies_fk", distinct=True))
        # falls du KEIN related_name vergeben hast, nimm:
        # return qs.annotate(_movie_count=Count("movie", distinct=True))

    @admin.display(description="Movies")
    def movie_count(self, obj):
        return getattr(obj, "_movie_count", 0)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'movie__title')