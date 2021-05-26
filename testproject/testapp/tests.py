from datetime import datetime, date, time
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from rest_framework_smoke.tests import checklists, mixins
from rest_framework_smoke.tests.schemas import (PAGINATE_SCHEMA, get_schema,
                                                get_array_schema,
                                                get_object_schema)
from testproject.testapp import models, schemas
from rest_framework.test import APIClient
from django_testing_utils.mixins import BaseTestCase


class BaseAPITestCase(APITestCase, BaseTestCase):
    pass


class ProjectViewSetTestCase(mixins.ReadOnlyViewSetTestsMixin,
                             checklists.ReadOnlyAPICheckList,
                             BaseAPITestCase):
    object_name = 'project'
    basename = 'projects'
    schema = details_schema = schemas.PROJECT_SCHEMA
    pagination_schema = None
    authentication = False

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('username', 'password')
        cls.project = models.Project.objects.create(name='project')
        cls.task = models.Task.objects.create(
            name='task',
            project=cls.project,
            author=cls.user
        )

    def test_read_permissions(self):
        """ Project list is accessible for anonymous users."""
        self.client.logout()
        self.assert_object_list(self.object_list)


# noinspection PyAbstractClass
class TaskViewSetTestCase(mixins.ReadViewSetTestsMixin,
                          mixins.CreateViewSetTestsMixin,
                          mixins.DeleteViewSetTestsMixin,
                          mixins.UpdateViewSetTestsMixin,
                          checklists.CompleteAPICheckList,
                          BaseAPITestCase):
    client: APIClient

    object_name = 'task'
    basename = 'tasks'
    schema = details_schema = schemas.TASK_SCHEMA
    pagination_schema = PAGINATE_SCHEMA
    authentication = True
    read_only_create_fields = ['author']
    read_only_update_fields = ['project']

    @classmethod
    def setUpTestData(cls):
        cls.project = models.Project.objects.create(name='project')
        cls.user = User.objects.create_user('login', password='password')
        cls.task = models.Task.objects.create(
            name='task',
            project=cls.project,
            author=cls.user)

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)

    def clone_object(self, obj: Model, **kwargs: Any) -> Model:
        """
        Default update tests implementations calls clone_object to alter
        ForeignKey values for updated objects.
        This may lead to unique key violation, so override default behavior to
        alter some fields while cloning.
        """
        if isinstance(obj, User):
            kwargs['username'] = obj.username + 'n'
        return super().clone_object(obj, **kwargs)

    def test_create_validation(self):
        """ Created tasks require a name and a project."""
        data = self.create({}, status=400)
        self.assertSetEqual(set(data), {'name', 'project'})

    def test_create_multipart(self):
        """ Just a smoke test to demonstrate multipart/form-data requests."""
        data = {'name': 'A name', 'project': self.project.id}
        data = self.perform_create(data, status=201, format='multipart')
        self.assertTrue(models.Task.objects.filter(
            pk=data['id'], name='A name', project=self.project).exists())

    def test_list_default_ordering(self):
        """ Tasks are sorted by name."""
        self.task2 = models.Task.objects.create(
            name='a',
            project=self.project,
            author=self.user)

        self.assert_object_list([self.task2, self.task])

        self.update_object(self.task2, name='z')

        self.assert_object_list([self.task, self.task2])

    def test_list_filter_params(self):
        """ Tasks can be filtered by project id."""
        p2 = models.Project.objects.create(name='p2')
        task2 = models.Task.objects.create(
            name='another',
            project=p2,
            author=self.user)

        self.assert_object_list([task2, self.task])

        self.assert_object_list([task2], query=dict(project=p2.pk))

    def test_partial_update_read_only_fields(self):
        """ Task project could not be updated via PATCH."""
        p2 = models.Project.objects.create(name='p2')

        self.update(data={'project': p2.pk}, status=200, partial=True)

        self.assert_object_fields(
            self.task,
            project=self.project)


class SchemaHelpersTestCase(SimpleTestCase):
    """ Tests for schema generation helpers."""

    def test_get_schema_from_json_schema_type_name(self):
        """
        Generating jsonschema type definition from type name
        """
        schema = get_schema("integer", enforce=False)
        expected = {"type": "integer"}
        self.assertEqual(schema, expected)

    def test_get_schema_from_python_type(self):
        """
        Generating jsonschema type definition from python type
        """
        cases = (
            (None, 'null', None),
            (int, 'integer', None),
            (float, 'number', None),
            (str, 'string', None),
            (bool, 'boolean', None),
            (datetime, 'string', 'date-time'),
            (date, 'string', 'date'),
            (time, 'string', 'time'),
        )
        for t, name, fmt in cases:
            with self.subTest(name):
                schema = get_schema(t, enforce=False)
                expected = {
                    "type": name
                }
                if fmt is not None:
                    expected["format"] = fmt
                self.assertDictEqual(schema, expected)

    def test_get_schema_for_list_of_types(self):
        """
        Generating a schema for a set of type variants.
        """
        schema = get_schema([None, int, "boolean"], enforce=False)
        expected = {
            "type": ["boolean", "integer", "null"]
        }
        self.assertDictEqual(schema, expected)

    def test_get_schema_for_an_object(self):
        """
        Generating a schema for a json object.
        """
        schema = get_schema({
            "id": int,
            "name": "string",
            "value": [None, float]
        }, enforce=False)
        expected = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "value": {"type": ["null", "number"]}
            }
        }
        self.assertDictEqual(schema, expected)

    def test_get_schema_for_an_array_of_objects(self):
        """
        Generating a schema for an array of json objects.
        """
        schema = get_schema([{"id": int}], enforce=False)
        expected = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"}
                }
            }
        }
        self.assertDictEqual(schema, expected)

    def test_compat_get_schema_for_an_array_of_types(self):
        """
        For backward compatibility schema for [bool] is not an array of boolean,
        but an element of single boolean type.
        """
        schema = get_schema([bool], enforce=False)
        expected = {"type": ["boolean"]}
        self.assertDictEqual(schema, expected)

    def test_get_schema_for_nested_object(self):
        """
        Generating schema for an object that contains nested object.
        """
        schema = get_schema({
            "id": int,
            "nested": {
                "name": "string"
            },
            "array": [{"slug": "string"}]
        }, enforce=False)
        expected = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "nested": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                },
                "array": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "slug": {"type": "string"}
                        }
                    }
                }
            }
        }
        self.assertDictEqual(schema, expected)

    def test_enforce_null_type_variant(self):
        """
        Enforcing schema removing null type variant from all types.
        """
        with self.subTest("remove null variant"):
            schema = get_schema([None, int], enforce=True)
            expected = {
                "type": ["integer"]
            }
            self.assertDictEqual(schema, expected)
        with self.subTest("skip enforce"):
            schema = get_schema([None, int], enforce=False)
            expected = {
                "type": ["integer", "null"]
            }
            self.assertDictEqual(schema, expected)
        with self.subTest("leave single null"):
            schema = get_schema([None], enforce=True)
            expected = {
                "type": ["null"]
            }
            self.assertDictEqual(schema, expected)

    def test_enforce_object_schema(self):
        """
        Enforcing object schema with restricting a set of properties and marking
        all of them as required.
        """
        with self.subTest("enforcing object schema"):
            schema = get_schema({"id": ["null", "integer"]}, enforce=True)
            expected = {
                "type": "object",
                "properties": {
                    "id": {"type": ["integer"]}
                },
                "required": ["id"],
                "additionalProperties": False
            }
            self.assertDictEqual(schema, expected)
        with self.subTest("skip enforcing object schema"):
            schema = get_schema({"id": ["null", "integer"]}, enforce=False)
            expected = {
                "type": "object",
                "properties": {
                    "id": {"type": ["integer", "null"]}
                }
            }
            self.assertDictEqual(schema, expected)

    def test_enforce_array_schema(self):
        """
        Enforcing array schema with min array length.
        """
        with self.subTest("enforcing array schema"):
            schema = get_schema([{"id": ["null", "integer"]}], enforce=True)
            expected = {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["integer"]}
                    },
                    "required": ["id"],
                    "additionalProperties": False
                }
            }
            self.assertDictEqual(schema, expected)
        with self.subTest("skip enforcing array schema"):
            schema = get_schema([{"id": ["null", "integer"]}], enforce=False)
            expected = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["integer", "null"]}
                    },
                }
            }
            self.assertDictEqual(schema, expected)

    def test_enforce_schema_recurse(self):
        """
        Enforcing schema for nested arrays and objects.
        """
        self.maxDiff = None
        schema = get_schema({
            "id": [None, int],
            "nested": {
                "name": "string",
            },
            "array": [{"slug": "string"}]
        }, enforce=True)
        expected = {
            "type": "object",
            "properties": {
                "id": {"type": ["integer"]},
                "nested": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"],
                    "additionalProperties": False
                },
                "array": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "slug": {"type": "string"}
                        },
                        "required": ["slug"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["id", "nested", "array"],
            "additionalProperties": False,
        }
        self.assertDictEqual(schema, expected)

    def test_bypass_object_schema(self):
        """
        A complete json object schema can be passed and it will not be modified.
        """
        schema = {
            'type': 'object'
        }

        self.assertIs(schema, get_object_schema(schema, enforce=False))

    def test_bypass_elem_schema(self):
        """
        A complete schema can be passed and will not be modified.
        """
        schema = {
            "type": "string"
        }
        self.assertIs(schema, get_schema(schema, enforce=False))

    def test_get_array_schema_for_an_ordinary_type(self):
        """
        Generating array schema for ordinary types.
        """
        schema = get_array_schema(float, enforce=False)
        expected = {
            "type": "array",
            "items": {"type": "number"}
        }
        self.assertDictEqual(schema, expected)

    def test_bypass_array_schema(self):
        """
        A complete json array schema can be passed and it will not be modified.
        """
        schema = {
            "type": "array"
        }
        self.assertIs(schema, get_array_schema(schema, enforce=False))

    def test_pass_full_schema_to_an_array(self):
        """
        A complete object schema can be passed to array schema and it will not
        be modified.
        """
        schema = {
            "type": "object"
        }

        result = get_schema([schema], enforce=False)
        self.assertIs(result["items"], schema)

    def test_merge_string_and_format(self):
        """
        When any string is allowed, types described by string with format are
        omitted.
        """
        schema = get_schema([str, datetime])
        expected = {
            "type": ["string"]
        }
        self.assertDictEqual(schema, expected)

    def test_pass_format_for_string(self):
        """
        When a type described via string with format is passed as single item
        in type list, format is passed to complete schema.
        """
        schema = get_schema([datetime])
        expected = {
            "type": ["string"],
            "format": "date-time",
        }
        self.assertDictEqual(schema, expected)
