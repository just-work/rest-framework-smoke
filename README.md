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

About schema checks
-------------------

Rest-Framework-Smoke uses `jsonschema` to validate API response format.
When we check format, we should pay attention to:
* no unexpected properties are found (is so, they are not validated by schema)
* there no missing properties (missing properties are not validated)
* arrays are not empty (because there is nothing to check in empty arrays)
* all values are not null (because null values mostly are null by default, and
    other type variants will never appear in schema validation code)

So there are two helpers in `rest_framework_smoke.tests.schemas` to enforce 
these constraints (and they are used internally for format tests):
* `get_object_schema`
* `get_array_schema`

