from typing import Iterable

PAGINATE_SCHEMA = {
    "next": {"type": ["string", "null"]},
    "previous": {"type": ["string", "null"]},
    "count": {"type": "integer", "minimum": 0},
}


def get_object_schema(schema, extra_types: Iterable = ()):
    """ Возвращает схему объекта
    В схеме может быть определён только перечень полей.
    В этом случае схема дополняется типом и признаками обязательности.
    """
    if "type" in schema and "properties" in schema:
        return schema
    return {
        "type": list({'object'} | set(extra_types)),
        "properties": schema,
        "required": list(schema.keys()),
        "additionalProperties": False
    }
