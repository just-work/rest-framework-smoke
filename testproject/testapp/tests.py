from rest_framework.test import APITestCase

from rest_framework_smoke.tests.mixins import ReadOnlyViewSetTestsMixin
from testproject.testapp import models, schemas


class ProjectViewSetTestCase(ReadOnlyViewSetTestsMixin, APITestCase):
    object_name = 'project'
    basename = 'projects'
    schema = details_schema = schemas.PROJECT_SCHEMA

    @classmethod
    def setUpTestData(cls):
        projects = [models.Project.objects.create(name='project%d' % n) for n
                    in range(3)]
        cls.project = projects[1]
        cls.task = models.Task.objects.create(name='task', project=cls.project)
