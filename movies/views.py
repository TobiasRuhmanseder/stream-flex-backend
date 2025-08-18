from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from movies.funktions import get_random_flag, parse_limit, pick_random
from .models import Movie, Genre
from .serializers import MovieSerializer, GenreSerializer


class MovieListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Movie.objects.filter(processing_status="ready").order_by('-created_at')
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


class GenreMoviesView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MovieSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return (
            Movie.objects.filter(genres__slug=slug)
            .order_by("-created_at")
            .select_related()  # optional: je nach Feldern
            .prefetch_related("genres")
        )
