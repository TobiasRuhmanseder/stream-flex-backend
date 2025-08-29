from __future__ import annotations

import pytest
from django.core.files.base import ContentFile

from movies.models import Movie
from movies.file_utils import delete_file_field, delete_many_file_fields


@pytest.mark.django_db
def test_delete_file_field_removes_file_from_storage_but_does_not_save_model():
    """
    Given a FileField with a stored file:
    - the file is removed from storage
    - the model is NOT saved (so DB value keeps the old name after refresh)
    """
    m = Movie.objects.create(title="X", description="x")
    m.thumbnail_image.save("thumb.jpg", ContentFile(b"img"), save=True)

    # Sanity: file exists in storage
    storage = m.thumbnail_image.storage
    name_in_db = m.thumbnail_image.name
    assert storage.exists(name_in_db)

    # Act
    delete_file_field(m, "thumbnail_image")

    # File should be gone from storage now
    assert not storage.exists(name_in_db)

    # Accessing the in-memory field usually shows empty name after .delete(save=False)
    assert m.thumbnail_image.name in ("", None)

    # But since we did NOT save the instance, the DB value still holds the old name
    m.refresh_from_db()
    assert m.thumbnail_image.name == name_in_db
    # And the file is still gone in storage
    assert not m.thumbnail_image.storage.exists(m.thumbnail_image.name)


@pytest.mark.django_db
def test_delete_file_field_gracefully_handles_missing_field():
    """
    If the field does not exist at all, the function should not raise.
    """
    m = Movie.objects.create(title="Y", description="y")
    # No exception expected
    delete_file_field(m, "this_field_does_not_exist")


@pytest.mark.django_db
def test_delete_file_field_gracefully_handles_blank_field():
    """
    If the field exists but has no name/file, the function should not raise.
    """
    m = Movie.objects.create(title="Z", description="z")
    assert m.hero_image.name == None  # never assigned
    delete_file_field(m, "hero_image")  # should be a no-op without error


@pytest.mark.django_db
def test_delete_many_file_fields_deletes_all_files():
    """
    delete_many_file_fields should delete every provided FileField's file.
    """
    m = Movie.objects.create(title="Multi", description="multi")
    m.thumbnail_image.save("thumb2.jpg", ContentFile(b"a"), save=True)
    m.hero_image.save("hero2.jpg", ContentFile(b"b"), save=True)

    s1, n1 = m.thumbnail_image.storage, m.thumbnail_image.name
    s2, n2 = m.hero_image.storage, m.hero_image.name
    assert s1.exists(n1)
    assert s2.exists(n2)

    delete_many_file_fields(m, ["thumbnail_image", "hero_image"])

    assert not s1.exists(n1)
    assert not s2.exists(n2)

    # DB values unchanged without save
    m.refresh_from_db()
    assert m.thumbnail_image.name == n1
    assert m.hero_image.name == n2