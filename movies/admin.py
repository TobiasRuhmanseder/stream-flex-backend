from django.contrib import admin
from django.db.models import Count
from .models import Favorite, Genre, Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "genres_display", "is_hero", "created_at")
    list_filter = ("is_hero", "created_at")
    search_fields = ("title", "description")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("genres")  # avoid N+1 at genres_display

    @admin.display(description="Genres")
    def genres_display(self, obj):
        names = [g.name for g in obj.genres.all()]
        return ", ".join(names) if names else "—"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "movie_count", "created_at")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_movie_count=Count("movies", distinct=True))

    @admin.display(description="Movies")
    def movie_count(self, obj):
        return getattr(obj, "_movie_count", 0)
    
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')
    list_filter  = ('created_at',)
    search_fields = ('user__email', 'movie__title')
