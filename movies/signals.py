import django_rq
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Movie
from .file_utils import delete_many_file_fields


@receiver(post_save, sender=Movie)
def enqueue_transcode(sender, instance, created, **kwargs):
    """Start video transcoding job when a new movie is created or missing transcoded files."""
    if not instance.video_file:
        return
    if created or not (instance.video_1080 and instance.video_720 and instance.video_480):
        queue = django_rq.get_queue("default")
        job_id = f"movie-{instance.pk}-transcode"
        if not queue.fetch_job(job_id):
            queue.enqueue("movies.tasks.process_movie", instance.pk, job_id=job_id)


@receiver(post_delete, sender=Movie)
def delete_files_on_movie_delete(sender, instance: Movie, **kwargs):
    """Remove all associated video and image files when a movie is deleted."""
    delete_many_file_fields(
        instance,
        [
            "video_file",
            "video_1080",
            "video_720",
            "video_480",
            "teaser_video",
            "hero_image",
            "thumbnail_image",
            "logo",
        ],
    )
