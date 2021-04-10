from django.contrib.auth.models import User
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
        cls.project = models.Project.objects.create(name='project')
        cls.task = models.Task.objects.create(name='task', project=cls.project)

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
    read_only_update_fields = ['project']

    @classmethod
    def setUpTestData(cls):
        cls.project = models.Project.objects.create(name='project')
        cls.task = models.Task.objects.create(name='task', project=cls.project)
        cls.user = User.objects.create_user('login', password='password')

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_create_validation(self):
        """ Created tasks require a name and a project."""
        data = self.create({}, status=400)
        self.assertSetEqual(set(data), {'name', 'project'})

    def test_list_default_ordering(self):
        """ Tasks are sorted by name."""
        self.task2 = models.Task.objects.create(name='a', project=self.project)

        self.assert_object_list([self.task2, self.task])

        self.update_object(self.task2, name='z')

        self.assert_object_list([self.task, self.task2])

    def test_list_filter_params(self):
        """ Tasks can be filtered by project id."""
        p2 = models.Project.objects.create(name='p2')
        task2 = models.Task.objects.create(name='another', project=p2)

        self.assert_object_list([task2, self.task])

        self.assert_object_list([task2], query=dict(project=p2.pk))

    def test_partial_update_read_only_fields(self):
        """ Task project could not be updated via PATCH."""
        p2 = models.Project.objects.create(name='p2')

        self.update(data={'project': p2.pk}, status=200, partial=True)

        self.assert_object_fields(
            self.task,
            project=self.project)
