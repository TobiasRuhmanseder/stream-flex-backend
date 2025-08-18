from django.urls import path
from .views import GenreListView, GenreMoviesView, HeroListView, MovieDetailView, MovieListCreateView

urlpatterns = [
    path("", MovieListCreateView.as_view(), name="movie-list"),
    path("movies/<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path('movies/heroes/', HeroListView.as_view(), name='movie-heroes'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('genres/<slug:slug>/movies/', GenreMoviesView.as_view(), name='genre-movies'),
]
