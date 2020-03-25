from copy import deepcopy

PAGINATE_SCHEMA = {
    "next": {"type": ["string", "null"]},
    "previous": {"type": ["string", "null"]},
    "count": {"type": "integer", "minimum": 0},
}


def get_array_schema(schema):
    """
    Returns more strict schema for an array of object with given schema.

    * arrays must have at least one member, because empty arrays silently
    satisfy any array item schema without an error.
    """
    if "minItems" in schema:
        return schema
    return {
        "type": ["array"],
        "minItems": 1,
        "items": get_object_schema(schema)
    }


def get_object_schema(schema):
    """
    Returns more strict schema based on passed object schema.

    * all attributes are set as required
    * no additional properties are allowed
    * nulls are not allowed because null variant effectively disables type
    checks for other variants if attribute is not set for checked object.
    """
    if "type" in schema and "properties" in schema:
        return schema

    schema = deepcopy(schema)
    for name, attribute in list(schema.items()):
        if "type" not in attribute:
            # don't know what it is
            continue
        # remove null because of high probability of type check skip
        attribute["type"] = [t for t in attribute["type"] if t != "null"]
        if attribute["type"] == ["object"]:
            # ensure that object schema is enforced
            schema[name] = get_object_schema(attribute["properties"])
        if attribute["type"] == ["array"]:
            # ensure that array schema is enforced
            schema[name] = get_array_schema(attribute["items"])

    return {
        "type": ['object'],
        "properties": schema,
        "required": list(schema.keys()),
        "additionalProperties": False
    }
