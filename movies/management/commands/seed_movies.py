from __future__ import annotations
from pathlib import Path
from typing import Optional
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from movies.models import Movie, Genre

# to create dummy-movies in the database
#
# docker compose exec web \
#   python manage.py seed_movies\
#   --movies 17 --heroes 2 \
#   --genre comedy\
#   --with-video /app/media/samples/demo.mp4 \
#   --transcode


LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
)


def pick_single_genre(explicit: Optional[str]) -> Genre:
    """
    Pick exactly one Genre.
    If `explicit` is given, match by slug (preferred) or name (case-insensitive).
    Otherwise pick a random Genre from the DB.
    """
    if explicit:
        g = (
            Genre.objects.filter(slug__iexact=explicit).first()
            or Genre.objects.filter(name__iexact=explicit).first()
        )
        if not g:
            raise CommandError(f"Genre '{explicit}' not found (by slug or name).")
        return g

    g = Genre.objects.order_by("?").first()
    if not g:
        raise CommandError("No genres exist. Please create at least one Genre first.")
    return g


class Command(BaseCommand):
    help = "Seed movies where each movie has exactly ONE genre (either a specified genre or a random one)."

    def add_arguments(self, parser):
        parser.add_argument("--movies", type=int, default=20, help="How many movies to create (default: 20).")
        parser.add_argument("--heroes", type=int, default=5, help="How many of them should be is_hero=true (default: 5).")
        parser.add_argument(
            "--genre",
            type=str,
            default=None,
            help="Use a single, specific genre for ALL movies (slug or name). If omitted, a random genre is chosen per movie.",
        )
        parser.add_argument(
            "--with-video",
            type=str,
            default=None,
            help="Container path to an MP4 to assign to each movie (e.g. /app/media/samples/demo.mp4).",
        )
        parser.add_argument(
            "--transcode",
            action="store_true",
            help="If set together with --with-video, mark movies as 'pending' so the post_save signal enqueues transcode jobs.",
        )

    def handle(self, *args, **opts):
        n_movies: int = opts["movies"]
        n_heroes: int = max(0, int(opts["heroes"]))
        genre_filter: Optional[str] = opts.get("genre")
        video_path: Optional[str] = opts.get("with_video")
        do_transcode: bool = bool(opts.get("transcode"))

        source_file: Optional[Path] = None
        if video_path:
            source_file = Path(video_path)
            if not source_file.exists():
                raise CommandError(f"--with-video file not found: {source_file}")

        # Pre-pick explicit genre once if provided (for ALL movies)
        explicit_genre: Optional[Genre] = None
        if genre_filter:
            explicit_genre = pick_single_genre(genre_filter)

        created_ids = []

        for i in range(n_movies):
            # pick exactly ONE genre (explicit or random per movie)
            genre = explicit_genre or pick_single_genre(None)

            is_hero = (i < n_heroes)

            # Decide initial processing status
            if source_file and do_transcode:
                processing_status = "pending"
            else:
                processing_status = "ready"

            title = f"Sample Movie {i + 1}"

            with transaction.atomic():
                movie = Movie.objects.create(
                    title=title,
                    description=LOREM,
                    is_hero=is_hero,
                    processing_status=processing_status,
                )

                # One-to-many assignment (exactly one Genre)
                movie.genre.set([genre])

                # Optional: attach the same source MP4
                if source_file:
                    with open(source_file, "rb") as fh:
                        # This only assigns the original file; your post_save signal/worker will build variants if --transcode given
                        movie.video_file.save(source_file.name, File(fh), save=False)

                movie.save()

                created_ids.append(movie.id)

            self.stdout.write(self.style.SUCCESS(f"Created movie #{movie.id} '{movie.title}' with genre '{genre.name}'"))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {len(created_ids)} movies. "
            f"{'Marked as pending for transcode.' if (source_file and do_transcode) else 'Marked as ready.'}"
        ))