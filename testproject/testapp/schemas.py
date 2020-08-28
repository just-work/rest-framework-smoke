TASK_SCHEMA = {
    "id": {"type": "number"},
    "name": {"type": ["string", "null"]},
}

PROJECT_SCHEMA = {
    "id": {"type": ["number"]},
    "name": {"type": ["string"]},
    "task_set": {
        "type": "array",
        "items": TASK_SCHEMA,
    }
}
