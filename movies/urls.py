from django.urls import path
from .views import (
    FavoriteListView,
    FavoriteView,
    GenreListView,
    GenreMoviesView,
    HeroImageView,
    HeroListView,
    LogoView,
    MovieDetailView,
    MovieListCreateView,
    ResolveSpeedView,
    SearchMoviesView,
    TeaserStreamView,
    ThumbnailView,
    VideoStreamView,
)

urlpatterns = [
    path("", MovieListCreateView.as_view(), name="movie-list"),
    path("<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("heroes/", HeroListView.as_view(), name="movie-heroes"),
    path("search/", SearchMoviesView.as_view(), name="movie-search"),
    path("genres/", GenreListView.as_view(), name="genre-list"),
    path("genres/<slug:slug>/", GenreMoviesView.as_view(), name="genre-movies"),
    path("<int:pk>/resolve-speed/", ResolveSpeedView.as_view(), name="resolve-speed"),
    path("<int:pk>/stream/", VideoStreamView.as_view(), name="video-stream"),
    path("<int:pk>/teaser/", TeaserStreamView.as_view(), name="teaser-stream"),
    path("<int:pk>/thumbnail/", ThumbnailView.as_view(), name="thumbnail"),
    path("<int:pk>/logo/", LogoView.as_view(), name="logo"),
    path("<int:pk>/hero-image/", HeroImageView.as_view(), name="hero-image"),
    path("api/movies/<int:pk>/favorite/", FavoriteView.as_view(), name="favorite"),
    path("api/movies/favorites/", FavoriteListView.as_view(), name="favorites"),
]
