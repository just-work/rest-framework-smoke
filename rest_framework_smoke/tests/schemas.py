from copy import deepcopy
from datetime import datetime, date, time
from functools import wraps
from typing import Dict, Any, Union, List, Tuple, Optional, Callable

AnyDict = Dict[str, Any]
AnyList = List[Any]

PAGINATE_SCHEMA = {
    "type": "object",
    "properties": {
        "next": {"type": [str, None]},
        "previous": {"type": [str, None]},
        "count": {"type": int, "minimum": 0},
    },
    "required": ["next", "previous", "count", "results"],
    "additionalProperties": False,
}

JSON_SCHEMA_TYPES: Dict[Optional[type], str] = {
    None: "null",
    int: "integer",
    float: "number",
    bool: "boolean",
    str: "string",
}

JSON_SCHEMA_FORMATS: Dict[type, str] = {
    datetime: "date-time",
    date: "date",
    time: "time",
}


def enforced(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(obj: Any, enforce: bool = True) -> Any:
        schema = func(obj)
        return enforce_schema(schema, enforce=enforce)

    return wrapper


@enforced
def get_object_schema(schema: AnyDict) -> AnyDict:
    """
    Transforms simplified schema to complete jsonschema object definition.

    * replaces single attribute type with list
    * replaces python types with jsonschema type names
    """
    if not isinstance(schema, dict):
        raise TypeError(schema)
    if schema.get('type') == 'object':
        # bypass
        return schema
    properties: AnyDict = {k: get_schema(v, False) for k, v in schema.items()}
    return {
        "type": "object",
        "properties": properties,
    }


@enforced
def get_array_schema(schema: Union[str, type, AnyDict]) -> AnyDict:
    """
    Transforms simplified schema to complete jsonschema array definition.
    """
    if isinstance(schema, (str, type)):
        # items type is pointing to a jsonschema type name or to a python type
        items: AnyDict = get_schema(schema, enforce=False)
    elif not isinstance(schema, dict):
        raise TypeError(schema)
    elif schema.get('type') == 'array':
        # bypass
        return schema
    elif 'type' in schema:
        # jsonschema passed, skip transforming
        items = schema
    else:
        # dict without type passed, transforming to object
        items = get_object_schema(schema, enforce=False)
    return {
        "type": "array",
        "items": items
    }


def translate_type(t: Union[str, type, None]) -> Tuple[str, Optional[str]]:
    """
    Translates python type to jsonschema type name

    :returns: type name, format name
    """
    if isinstance(t, str):
        return t, None
    if t is None:
        return 'null', None
    if not isinstance(t, type):
        raise TypeError(t)
    try:
        name = JSON_SCHEMA_TYPES[t]
        fmt = None
    except KeyError:
        name = 'string'
        fmt = JSON_SCHEMA_FORMATS[t]
    return name, fmt


@enforced
def get_schema(attr: Union[str, type, None, AnyDict, AnyList]) -> AnyDict:
    """
    Returns jsonschema type definition from:
    * jsonschema type name,
    * python type,
    * array simplified definition,
    * object simplified definition
    * jsonschema type definition

    >>> from datetime import *
    >>> get_schema(None)
    {'type': 'null'}
    >>> get_schema(str)
    {'type': 'string'}
    >>> get_schema("number")
    {'type': 'number'}
    >>> get_schema([float, bool])
    {'type': ['boolean', 'number']}
    >>> get_schema([datetime])
    {'type': ['string'], 'format': 'date-time'}
    >>> get_schema({"id": int})
    {'type': 'object', 'properties': {'id': {'type': 'integer'}}}
    >>> get_schema([{"id": int}])
    {'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'integer'}}}}
    >>>
    """
    if isinstance(attr, list):
        # [{object definition}]
        if isinstance(attr[0], dict):
            return get_array_schema(attr[0], enforce=False)
        # a set of type variants passed
        type_names = set()
        string_formats = set()
        for a in attr:
            name, fmt = translate_type(a)
            if fmt is not None and (str in attr or 'string' in attr):
                # Disabling formatted string, if string is already present.
                # String and datetime could not be expressed together,
                # because "date-time" format will break "string" type.
                fmt = None
            if fmt is not None:
                string_formats.add(fmt)
            type_names.add(name)
        result: AnyDict = {
            "type": list(sorted(type_names))
        }
        if len(string_formats) == 1:
            # jsonschema will scheck only single allowed format
            result["format"] = string_formats.pop()
        return result
    if isinstance(attr, dict):
        # {content} is either jsonschema definition or a shortcut for an object
        if 'type' in attr:
            # jsonschema definition, bypass
            return attr
        return get_object_schema(attr, enforce=False)
    # all other type variants are ordinal types
    name, fmt = translate_type(attr)
    result = {
        "type": name,
    }
    if fmt is not None:
        result["format"] = fmt
    return result


def enforce_schema(schema: dict, enforce: bool = True) -> dict:
    """
    Enforces some constraints on a json schema to allow more robust format
    checking

    * all object attributes are set as required.
    * no additional object properties are allowed.
    * nulls are not allowed because null variant effectively disables type
    checks for other variants if attribute is not set for checked object.
    * min length is added to arrays because empty array satisfy any item schema.
    """
    if not enforce:
        return schema
    if not isinstance(schema, dict):
        # unknown type, bypass
        return schema
    try:
        schema_type = schema['type']
    except KeyError:
        # type is missing
        return schema

    schema = deepcopy(schema)
    if schema_type == 'object':
        # no additional object attributes are allowed
        schema.setdefault("additionalProperties", False)
        # all object attributes are required
        schema.setdefault("required", list(schema["properties"]))

        properties = {}
        for k, subschema in schema["properties"].items():
            properties[k] = enforce_schema(subschema)
        schema["properties"] = properties
    elif schema_type == 'array':
        # any array must not be empty
        schema.setdefault("minItems", 1)
        schema["items"] = enforce_schema(schema["items"])
        return schema
    elif (isinstance(schema_type, list) and
          'null' in schema_type and
          len(schema_type) > 1):
        # removing null from type variants, if it is not the only one.
        schema["type"] = [t for t in schema_type if t != "null"]

    # no constraints for types other than object and array
    return schema
#
#
# def get_array_schema(schema: dict) -> dict:
#     """
#     Returns more strict schema for an array of object with given schema.
#
#     * arrays must have at least one member, because empty arrays silently
#     satisfy any array item schema without an error.
#     """
#     if "minItems" in schema:
#         return schema
#     return {
#         "type": ["array"],
#         "minItems": 1,
#         "items": get_object_schema(schema["items"])
#     }
#
#
# def get_object_schema(schema: dict) -> dict:
#     """
#     Returns more strict schema based on passed object schema.
#
#     * all attributes are set as required
#     * no additional properties are allowed
#     * nulls are not allowed because null variant effectively disables type
#     checks for other variants if attribute is not set for checked object.
#     """
#     if "type" in schema and "properties" in schema:
#         return schema
#
#     schema = deepcopy(schema)
#     for name, attribute in list(schema.items()):
#         if "type" not in attribute:
#             # don't know what it is
#             continue
#         if isinstance(attribute["type"], str):
#             attribute["type"] = [attribute["type"]]
#         elif isinstance(attribute["type"], (list, tuple)):
#             # remove null because of high probability of type check skip
#             attribute["type"] = [t for t in attribute["type"] if t != "null"]
#
#         if attribute["type"] == ["object"]:
#             # ensure that object schema is enforced
#             schema[name] = get_object_schema(attribute["properties"])
#         if attribute["type"] == ["array"]:
#             # ensure that array schema is enforced
#             schema[name] = get_array_schema(attribute)
#
#     return {
#         "type": ['object'],
#         "properties": schema,
#         "required": list(schema.keys()),
#         "additionalProperties": False
#     }
