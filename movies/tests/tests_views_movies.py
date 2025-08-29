from io import BytesIO
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path, reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from movies.models import Movie, Genre, Favorite
from movies.views import (
    MovieListCreateView,
    MovieDetailView,
    SearchMoviesView,
    HeroListView,
    GenreListView,
    GenreMoviesView,
    ResolveSpeedView,
    VideoStreamView,
    TeaserStreamView,
    ThumbnailView,
    LogoView,
    HeroImageView,
    FavoriteView,
    FavoriteListView,
)

# --- Test-local URLConf (so we don't depend on your project urls) ---
urlpatterns = [
    path("", MovieListCreateView.as_view(), name="t-movie-list"),
    path("<int:pk>/", MovieDetailView.as_view(), name="t-movie-detail"),
    path("search/", SearchMoviesView.as_view(), name="t-movie-search"),
    path("hero/", HeroListView.as_view(), name="t-movie-hero"),
    path("genres/", GenreListView.as_view(), name="t-genre-list"),
    path("genres/<slug:slug>/", GenreMoviesView.as_view(), name="t-genre-movies"),
    path("<int:pk>/resolve-speed/", ResolveSpeedView.as_view(), name="t-resolve-speed"),

    # File/stream endpoints (name 'video-stream' is required by ResolveSpeedView)
    path("<int:pk>/stream/", VideoStreamView.as_view(), name="video-stream"),
    path("<int:pk>/teaser/", TeaserStreamView.as_view(), name="t-teaser"),
    path("<int:pk>/thumbnail/", ThumbnailView.as_view(), name="t-thumb"),
    path("<int:pk>/logo/", LogoView.as_view(), name="t-logo"),
    path("<int:pk>/hero-image/", HeroImageView.as_view(), name="t-hero-img"),

    # Favorites
    path("<int:pk>/favorite/", FavoriteView.as_view(), name="t-fav"),
    path("favorites/", FavoriteListView.as_view(), name="t-fav-list"),
]


@override_settings(ROOT_URLCONF=__name__)
class MovieAPITests(APITestCase):
    """
    High-level API tests hitting real DRF stack (router/middleware/etc. via APIClient).
    We keep tests realistic but patch internal helpers where touching files is needed.
    """

    def setUp(self):
        self.client: APIClient = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="tester@example.com", email="tester@example.com", password="pw12345!")
        self.client.force_authenticate(user=self.user)

        # Common URLs
        self.url_list = reverse("t-movie-list")
        self.url_search = reverse("t-movie-search")
        self.url_hero = reverse("t-movie-hero")
        self.url_genres = reverse("t-genre-list")

        # Simple genres
        self.g_action = Genre.objects.create(name="Action", slug="action")
        self.g_drama = Genre.objects.create(name="Drama", slug="drama")

        # Helper to create a "ready" movie
        self.m1 = Movie.objects.create(title="Alpha", description="first", processing_status="ready", is_hero=False)
        self.m1.genres.add(self.g_action)
        self.m2 = Movie.objects.create(title="Bravo", description="second", processing_status="ready", is_hero=True)
        self.m2.genres.add(self.g_action, self.g_drama)
        self.m3 = Movie.objects.create(title="Charlie", description="third", processing_status="pending", is_hero=True)  # not ready

    # -----------------------------
    # MovieListCreateView (GET)
    # -----------------------------
    def test_movie_list_returns_ready_movies_and_marks_favorites(self):
        # mark m2 as favorite
        Favorite.objects.create(user=self.user, movie=self.m2)

        res = self.client.get(self.url_list)
        assert res.status_code == status.HTTP_200_OK
        # Only ready movies (m1, m2), not m3
        titles = [m["title"] for m in res.data]
        assert "Alpha" in titles and "Bravo" in titles and "Charlie" not in titles

    def test_movie_list_can_filter_by_genre(self):
        # ?genre=drama -> only m2
        res = self.client.get(self.url_list, {"genre": "drama"})
        assert res.status_code == status.HTTP_200_OK
        assert [m["title"] for m in res.data] == ["Bravo"]

    # -----------------------------
    # MovieDetailView (GET)
    # -----------------------------
    def test_movie_detail_ok_and_404_when_not_ready(self):
        # ok for ready
        url_ok = reverse("t-movie-detail", args=[self.m1.pk])
        res_ok = self.client.get(url_ok)
        assert res_ok.status_code == status.HTTP_200_OK
        assert res_ok.data["title"] == "Alpha"

        # 404 when not ready
        url_404 = reverse("t-movie-detail", args=[self.m3.pk])
        res_404 = self.client.get(url_404)
        assert res_404.status_code == status.HTTP_404_NOT_FOUND

    # -----------------------------
    # SearchMoviesView (GET)
    # -----------------------------
    def test_search_movies_empty_and_with_query(self):
        # q empty -> all ready ordered
        res_all = self.client.get(self.url_search, {"q": ""})
        assert res_all.status_code == status.HTTP_200_OK
        titles = [m["title"] for m in res_all.data]
        assert set(titles) == {"Alpha", "Bravo"}

        # q 'br' -> "Bravo"
        res_q = self.client.get(self.url_search, {"q": "br"})
        assert res_q.status_code == status.HTTP_200_OK
        assert [m["title"] for m in res_q.data] == ["Bravo"]

    # -----------------------------
    # HeroListView (GET)
    # -----------------------------
    @patch("movies.views.parse_limit", return_value=2)
    def test_hero_list_randomize_and_no_results(self, p_limit):
        # Case 1: no ready hero -> []
        self.m2.processing_status = "pending"
        self.m2.save(update_fields=["processing_status"])
        res_empty = self.client.get(self.url_hero)
        assert res_empty.status_code == status.HTTP_200_OK
        assert res_empty.data == []

        # Case 2: ready hero exists; randomize False -> most recent first (limited)
        self.m2.processing_status = "ready"
        self.m2.save(update_fields=["processing_status"])
        with patch("movies.views.get_random_flag", return_value=False):
            res = self.client.get(self.url_hero)
        assert res.status_code == status.HTTP_200_OK
        titles = [m["title"] for m in res.data]
        # includes m2 (hero, ready). m1 is not hero.
        assert "Bravo" in titles

        # Case 3: randomize True -> pick_random() path
        with patch("movies.views.get_random_flag", return_value=True), \
             patch("movies.views.pick_random", return_value=[self.m2]):
            res_rnd = self.client.get(self.url_hero)
        assert res_rnd.status_code == status.HTTP_200_OK
        titles_rnd = [m["title"] for m in res_rnd.data]
        assert titles_rnd  # not empty when hero exists

    # -----------------------------
    # Genre list & movies by genre
    # -----------------------------
    def test_genre_list(self):
        res = self.client.get(self.url_genres)
        assert res.status_code == status.HTTP_200_OK
        slugs = [g["slug"] for g in res.data]
        assert set(slugs) >= {"action", "drama"}

    def test_genre_movies_lists_ready_only(self):
        url = reverse("t-genre-movies", args=["action"])
        res = self.client.get(url)
        assert res.status_code == status.HTTP_200_OK
        titles = [m["title"] for m in res.data]
        assert "Alpha" in titles and "Bravo" in titles and "Charlie" not in titles

    # -----------------------------
    # ResolveSpeedView
    # -----------------------------
    

    def test_resolve_speed_builds_stream_url_and_quality(self):
        url = reverse("t-resolve-speed", args=[self.m2.pk])
        with patch("movies.views.choose_quality", return_value=("720p", "ok")):
            res = self.client.get(url, {"downlink": "10.5", "screen_h": "1080"})

        assert res.status_code == status.HTTP_200_OK
        data = res.data
        assert data["movie_id"] == self.m2.pk
        assert data["quality"] == "720p"

        # URL validieren (Pfad + Query)
        parsed = urlparse(data["url"])
        assert parsed.path.endswith(f"/{self.m2.pk}/stream/")   # Pfad stimmt
        qs = parse_qs(parsed.query)
        assert qs.get("q") == ["720p"]                          # Query-Param stimmt

    def test_resolve_speed_handles_bad_query_params(self):
        url = reverse("t-resolve-speed", args=[self.m2.pk])
        with patch("movies.views.choose_quality", return_value=("480p", "low")):
            res = self.client.get(url, {"downlink": "not-a-float", "screen_h": "NaN"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["quality"] == "480p"

    # -----------------------------
    # Streaming & media endpoints (patch file access)
    # -----------------------------
    def _fake_file(self, name):
        buf = BytesIO(b"fake-bytes")
        buf.name = name
        return buf

    @patch("movies.views.getSource", return_value="any.mp4")
    @patch("movies.views.check_or_404")
    def test_video_stream_returns_file_response(self, p_check, p_src):
        p_check.return_value = self._fake_file("video.mp4")
        url = reverse("video-stream", args=[self.m2.pk])
        res = self.client.get(url, {"q": "720p"})
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "video/mp4"
        assert "Cache-Control" in res

    @patch("movies.views.check_or_404")
    def test_teaser_stream_ok(self, p_check):
        p_check.return_value = self._fake_file("teaser.mp4")
        url = reverse("t-teaser", args=[self.m2.pk])
        res = self.client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "video/mp4"

    @patch("movies.views.check_or_404")
    def test_thumbnail_and_logo_and_hero_image_content_types(self, p_check):
        # thumbnail (image/jpeg)
        p_check.return_value = self._fake_file("thumb.jpg")
        res_thumb = self.client.get(reverse("t-thumb", args=[self.m2.pk]))
        assert res_thumb.status_code == status.HTTP_200_OK
        assert res_thumb["Content-Type"].startswith("image/")

        # logo (image/png)
        p_check.return_value = self._fake_file("logo.png")
        res_logo = self.client.get(reverse("t-logo", args=[self.m2.pk]))
        assert res_logo.status_code == status.HTTP_200_OK
        assert res_logo["Content-Type"].startswith("image/")

        # hero-image (image/jpeg)
        p_check.return_value = self._fake_file("hero.jpg")
        res_hero = self.client.get(reverse("t-hero-img", args=[self.m2.pk]))
        assert res_hero.status_code == status.HTTP_200_OK
        assert res_hero["Content-Type"].startswith("image/")

    # -----------------------------
    # Favorites (POST/DELETE + listing)
    # -----------------------------
    def test_favorite_add_and_delete_are_idempotent(self):
        url = reverse("t-fav", args=[self.m1.pk])

        # POST add (201)
        res1 = self.client.post(url, {}, format="json")
        assert res1.status_code == status.HTTP_201_CREATED
        assert Favorite.objects.filter(user=self.user, movie=self.m1).count() == 1

        # POST add again (still 201, still only one favorite)
        res2 = self.client.post(url, {}, format="json")
        assert res2.status_code == status.HTTP_201_CREATED
        assert Favorite.objects.filter(user=self.user, movie=self.m1).count() == 1

        # DELETE (204)
        res3 = self.client.delete(url)
        assert res3.status_code == status.HTTP_204_NO_CONTENT
        assert Favorite.objects.filter(user=self.user, movie=self.m1).exists() is False

        # DELETE again (still 204, idempotent)
        res4 = self.client.delete(url)
        assert res4.status_code == status.HTTP_204_NO_CONTENT

    def test_favorite_list_returns_only_ready_favorites(self):
        Favorite.objects.create(user=self.user, movie=self.m1)  # ready
        Favorite.objects.create(user=self.user, movie=self.m3)  # not ready
        url = reverse("t-fav-list")
        res = self.client.get(url)
        assert res.status_code == status.HTTP_200_OK
        titles = [m["title"] for m in res.data]
        assert "Alpha" in titles and "Charlie" not in titles