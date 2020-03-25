from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from rest_framework_smoke.tests.mixins import ReadOnlyViewSetTestsMixin
from testproject.testapp import models, schemas

User = get_user_model()


class ProjectViewSetTestCase(ReadOnlyViewSetTestsMixin, APITestCase):
    object_name = 'project'
    basename = 'projects'
    schema = details_schema = schemas.PROJECT_SCHEMA
    pagination_schema = None

    @classmethod
    def setUpTestData(cls):
        cls.project = models.Project.objects.create(name='project')
        cls.task = models.Task.objects.create(name='task', project=cls.project)
        cls.user = User.objects.create()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
