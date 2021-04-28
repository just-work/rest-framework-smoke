PROJECT_TASK_SCHEMA = {
    "id": int,
    "name": [None, str],
    "author": int,
}

PROJECT_SCHEMA = {
    "id": int,
    "name": str,
    "task_set": [PROJECT_TASK_SCHEMA]
}

TASK_SCHEMA = {
    "id": int,
    "project": int,
    "name": [None, str],
    "author": int,
}
