from typing import Any

from django.contrib.auth.models import User
from django.db.models import Model
from rest_framework.test import APITestCase

from rest_framework_smoke.tests import checklists, mixins
from rest_framework_smoke.tests.schemas import PAGINATE_SCHEMA
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
