import mimetypes
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from movies.funktions import check_or_404, choose_quality, get_random_flag, getSource, parse_limit, pick_random
from .models import Favorite, Movie, Genre
from .serializers import MovieSerializer, GenreSerializer


class MovieListCreateView(APIView):
    """Return a list of movies. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorite_ids = set(Favorite.objects.filter(user=request.user).values_list("movie_id", flat=True))
        qs = Movie.objects.filter(processing_status="ready").order_by("-created_at")
        genre_slug = request.query_params.get("genre")
        if genre_slug:
            qs = qs.filter(genre__slug=genre_slug)
        ser = MovieSerializer(qs, many=True, context={"request": request, "favorite_ids": favorite_ids})
        return Response(ser.data, status=status.HTTP_200_OK)


class MovieDetailView(APIView):
    """Return detail of a single movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        ser = MovieSerializer(movie, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class SearchMoviesView(generics.ListAPIView):
    """Search movies by title or description. User must be logged in."""
    permission_classes = [IsAuthenticated]
    serializer_class = MovieSerializer

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        qs = Movie.objects.filter(processing_status="ready").prefetch_related("genre")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        return qs.order_by("-created_at").distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        fav_ids = set(Favorite.objects.filter(user=self.request.user).values_list("movie_id", flat=True))
        context["favorite_ids"] = fav_ids
        return context


class HeroListView(APIView):
    """Return a list of hero movies. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorite_ids = set(Favorite.objects.filter(user=request.user).values_list("movie_id", flat=True))
        qs = Movie.objects.filter(is_hero=True, processing_status="ready")
        if not qs.exists():
            return Response([], status=status.HTTP_200_OK)

        limit = parse_limit(request, default=3, min_value=1, max_value=10)
        randomize = get_random_flag(request, default=False)
        movies = pick_random(qs, limit) if randomize else list(qs.order_by("-created_at")[:limit])
        ser = MovieSerializer(qs, many=True, context={"request": request, "favorite_ids": favorite_ids})
        return Response(ser.data, status=status.HTTP_200_OK)


class GenreListView(generics.ListAPIView):
    """Return a list of all genres. Anyone can access."""
    permission_classes = [AllowAny]
    serializer_class = GenreSerializer
    queryset = Genre.objects.all().order_by("name")


class GenreMoviesView(generics.ListAPIView):
    """Return movies for a specific genre. User must be logged in."""
    permission_classes = [IsAuthenticated]
    serializer_class = MovieSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return Movie.objects.filter(genre__slug=slug, processing_status="ready").order_by("-created_at").prefetch_related("genre")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        fav_ids = set(Favorite.objects.filter(user=self.request.user).values_list("movie_id", flat=True))
        context["favorite_ids"] = fav_ids
        return context


class ResolveSpeedView(APIView):
    """Determine best video quality based on speed and screen height. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        dl_raw = request.query_params.get("downlink")
        sh_raw = request.query_params.get("screen_h")
        try:
            downlink = float(dl_raw) if dl_raw is not None else None
        except Exception:
            downlink = None
        try:
            screen_h = int(sh_raw) if sh_raw is not None else None
        except Exception:
            screen_h = None

        has_1080 = bool(movie.video_1080 and getattr(movie.video_1080, "name", None))
        has_720 = bool(movie.video_720 and getattr(movie.video_720, "name", None))
        has_480 = bool(movie.video_480 and getattr(movie.video_480, "name", None))

        quality, msg_key = choose_quality(
            has_1080=has_1080, has_720=has_720, has_480=has_480, screen_h=screen_h, downlink_mbps=downlink
        )
        stream_path = reverse("video-stream", args=[movie.pk]) + f"?q={quality}"
        url = request.build_absolute_uri(stream_path)

        return Response(
            {"movie_id": movie.pk,"quality": quality,"url": url,"message_key": msg_key,},
            status=status.HTTP_200_OK,
        )


class VideoStreamView(APIView):
    """Stream video file for a movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        q = (request.query_params.get("q") or "").strip()
        src = getSource(movie, q)
        file = check_or_404(src)
        resp = FileResponse(file, content_type="video/mp4")
        resp["Cache-Control"] = "private, max-age=300"
        return resp


class TeaserStreamView(APIView):
    """Stream teaser video for a movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        file = check_or_404(movie.teaser_video)
        resp = FileResponse(file, content_type="video/mp4")
        resp["Cache-Control"] = "private, max-age=300"
        return resp


class ThumbnailView(APIView):
    """Serve thumbnail image for a movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        file = check_or_404(movie.thumbnail_image)
        ct, _ = mimetypes.guess_type(file.name)
        resp = FileResponse(file, content_type=ct or "image/jpeg")
        resp["Cache-Control"] = "private, max-age=600"
        return resp


class LogoView(APIView):
    """Serve logo image for a movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        file = check_or_404(movie.logo)
        ct, _ = mimetypes.guess_type(file.name)
        resp = FileResponse(file, content_type=ct or "image/png")
        resp["Cache-Control"] = "private, max-age=600"
        return resp


class HeroImageView(APIView):
    """Serve hero image for a movie. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        movie = get_object_or_404(Movie, pk=pk, processing_status="ready")
        file = check_or_404(movie.hero_image)
        ct, _ = mimetypes.guess_type(file.name)
        resp = FileResponse(file, content_type=ct or "image/jpeg")
        resp["Cache-Control"] = "private, max-age=600"
        return resp


class FavoriteView(APIView):
    """Add or remove a movie from user's favorites. User must be logged in."""
    permission_classes = [IsAuthenticated]

    # POST /api/movies/<pk>/favorite/  → add (idempotent)
    def post(self, request, pk: int):
        movie = get_object_or_404(Movie, pk=pk)
        Favorite.objects.get_or_create(user=request.user, movie=movie)
        return Response({"detail": "added"}, status=status.HTTP_201_CREATED)

    # DELETE /api/movies/<pk>/favorite/ → remove (idempotent)
    def delete(self, request, pk: int):
        Favorite.objects.filter(user=request.user, movie_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListView(APIView):
    """Return list of user's favorite movies. User must be logged in."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Movie.objects.filter(favorited_by__user=request.user, processing_status="ready").order_by("-favorited_by__created_at")

        favorite_ids = set(qs.values_list("id", flat=True))
        ser = MovieSerializer(qs, many=True, context={"request": request, "favorite_ids": favorite_ids})
        return Response(ser.data, status=status.HTTP_200_OK)
