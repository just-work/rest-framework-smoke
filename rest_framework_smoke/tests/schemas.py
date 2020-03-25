PAGINATE_SCHEMA = {
    "next": {"type": ["string", "null"]},
    "previous": {"type": ["string", "null"]},
    "count": {"type": "integer", "minimum": 0},
}


def get_object_schema(schema):
    """
    Returns more strict schema based on passed object schema.

    * all attributes are set as required
    * no additional properties are allowed

    This is needed to check that returned keys are present and have expected
    type.

    More tips to define schema:

    * arrays must have at least one member, because empty array items silently
    satisfy any array item schema without an error.
    * there must be no null values for nested objects, because null variant
    effectively disables schema checks for a nested object.
    """
    if "type" in schema and "properties" in schema:
        return schema
    return {
        "type": ['object'],
        "properties": schema,
        "required": list(schema.keys()),
        "additionalProperties": False
    }
