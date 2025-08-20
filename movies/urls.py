from django.urls import path
from .views import GenreListView, GenreMoviesView, HeroListView, LogoView, MovieDetailView, MovieListCreateView, ResolveSpeedView, TeaserStreamView, ThumbnailView, VideoStreamView

urlpatterns = [
    path("", MovieListCreateView.as_view(), name="movie-list"),
    path("<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("heroes/", HeroListView.as_view(), name="movie-heroes"),
    path("genres/", GenreListView.as_view(), name="genre-list"),
    path("genres/<slug:slug>/", GenreMoviesView.as_view(), name="genre-movies"),
    path("<int:pk>/resolve-speed/", ResolveSpeedView.as_view(), name="resolve-speed"),
    path("<int:pk>/stream/", VideoStreamView.as_view(), name="video-stream"),
    path("<int:pk>/teaser/", TeaserStreamView.as_view(), name="teaser-stream"),
    path("<int:pk>/thumbnail/", ThumbnailView.as_view(), name="thumbnail"),
    path("<int:pk>/logo/", LogoView.as_view(), name="logo"),
]
