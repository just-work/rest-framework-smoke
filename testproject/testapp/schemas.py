from rest_framework_smoke.tests.schemas import get_object_schema

TASK_SCHEMA = {
    "id": {"type": ["number"]},
    "name": {"type": ["string"]},
}

PROJECT_SCHEMA = {
    "id": {"type": ["number"]},
    "name": {"type": ["string"]},
    "task_set": {
        "type": ["array"],
        "minItems": 1,
        "items": get_object_schema(TASK_SCHEMA)
    }
}
