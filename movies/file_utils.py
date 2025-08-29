from typing import Iterable


def delete_file_field(instance, field_name: str) -> None:
    """
    Deletes the file associated with a given field from an instance and its storage.

    Args:
        instance: The object containing the file field.
        field_name (str): The name of the file field to delete.
    """
    f = getattr(instance, field_name, None)
    try:
        if f and getattr(f, "name", ""):
            storage = f.storage
            name = f.name
            # 1) DB-Feld nicht erneut speichern (wir sind z.B. in post_delete)
            f.delete(save=False)
            # 2) Sicherstellen, dass die Datei im Storage wirklich weg ist
            if storage.exists(name):
                storage.delete(name)
    except Exception:
        # nie den Löschvorgang abbrechen
        pass


def delete_many_file_fields(instance, fields: Iterable[str]) -> None:
    """
    Deletes files from multiple fields of an instance and their storage.

    Args:
        instance: The object containing the file fields.
        fields (Iterable[str]): The names of the file fields to delete.
    """
    for name in fields:
        delete_file_field(instance, name)
