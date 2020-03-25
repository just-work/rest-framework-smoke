Rest-Framework-Smoke
====================

Smoke tests for API built with Django Rest Framework.

[![Build Status](https://travis-ci.org/just-work/rest-framework-smoke.svg?branch=master)](https://travis-ci.org/just-work/rest-framework-smoke)
[![codecov](https://codecov.io/gh/just-work/rest-framework-smoke/branch/master/graph/badge.svg)](https://codecov.io/gh/just-work/rest-framework-smoke)
[![PyPI version](https://badge.fury.io/py/rest-framework-smoke.svg)](https://badge.fury.io/py/rest-framework-smoke)

Installation
------------

```shell script
pip install rest-framework-smoke
```

Usage
-----

Full example located at `testproject.testapp.tests`

```python
from rest_framework.test import APITestCase

from rest_framework_smoke.tests.mixins import ReadOnlyViewSetTestsMixin
from rest_framework_smoke.tests.schemas import get_object_schema
from testproject.testapp import models

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


class ProjectViewSetTestCase(ReadOnlyViewSetTestsMixin, APITestCase):
    object_name = 'project'
    basename = 'projects'
    schema = details_schema = PROJECT_SCHEMA
    pagination_schema = None

    @classmethod
    def setUpTestData(cls):
        cls.project = models.Project.objects.create(name='project')
        cls.task = models.Task.objects.create(name='task', project=cls.project)
```

Happy API testing :)
