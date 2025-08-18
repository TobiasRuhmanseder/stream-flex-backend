from typing import Iterable


def delete_file_field(instance, field_name: str) -> None:
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
    for name in fields:
        delete_file_field(instance, name)
