import mimetypes
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from movies.funktions import check_or_404, choose_quality, get_random_flag, getSource, parse_limit, pick_random
from .models import Movie, Genre
from .serializers import MovieSerializer, GenreSerializer


class MovieListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Movie.objects.filter(processing_status="ready").order_by("-created_at")
        genre_slug = request.query_params.get("genre")
        if genre_slug:
            qs = qs.filter(genres__slug=genre_slug)
        ser = MovieSerializer(qs, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class MovieDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        movie = get_object_or_404(Movie, pk=pk)
        ser = MovieSerializer(movie, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class HeroListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Movie.objects.filter(is_hero=True)
        if not qs.exists():
            return Response([], status=status.HTTP_200_OK)

        limit = parse_limit(request, default=3, min_value=1, max_value=10)
        randomize = get_random_flag(request, default=False)
        movies = pick_random(qs, limit) if randomize else list(qs.order_by("-created_at")[:limit])
        ser = MovieSerializer(movies, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class GenreListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = GenreSerializer
    queryset = Genre.objects.all().order_by("name")


class GenreMoviesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MovieSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return (
            Movie.objects.filter(genres__slug=slug)
            .order_by("-created_at")
            .select_related() 
            .prefetch_related("genres")
        )

class ResolveSpeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
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

        stream_path = reverse("movies:video-stream", args=[movie.pk]) + f"?q={quality}"
        url = request.build_absolute_uri(stream_path)

        return Response({"movie_id": movie.pk, "quality": quality, "url": url, "message_key": msg_key,}, status=status.HTTP_200_OK)
    
class VideoStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        q = (request.query_params.get("q") or "").strip()
        src = getSource(movie, q)
        file = check_or_404(src)

        resp = FileResponse(file, content_type="video/mp4")
        resp["Cache-Control"] = "private, max-age=300"
        return resp
    

class TeaserStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        file = check_or_404(movie.teaser_video)
        resp = FileResponse(file, content_type="video/mp4")
        resp["Cache-Control"] = "private, max-age=300"
        return resp


class ThumbnailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        file = check_or_404(movie.thumbnail_image)
        ct, _ = mimetypes.guess_type(file.name)
        resp = FileResponse(file, content_type=ct or "image/jpeg")
        resp["Cache-Control"] = "private, max-age=600"
        return resp

class LogoView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        file = check_or_404(movie.logo)
        ct, _ = mimetypes.guess_type(file.name)
        resp = FileResponse(file, content_type=ct or "image/png")
        resp["Cache-Control"] = "private, max-age=600"
        return resp