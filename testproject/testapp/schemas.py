PROJECT_TASK_SCHEMA = {
    "id": {"type": "number"},
    "name": {"type": ["string", "null"]},
}

PROJECT_SCHEMA = {
    "id": {"type": ["number"]},
    "name": {"type": ["string"]},
    "task_set": {
        "type": "array",
        "items": PROJECT_TASK_SCHEMA,
    }
}

TASK_SCHEMA = {
    "id": {"type": "number"},
    "project": {"type": "number"},
    "name": {"type": ["string", "null"]},
}
