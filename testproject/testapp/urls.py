from rest_framework.routers import SimpleRouter

from testproject.testapp import views

router = SimpleRouter()

router.register('projects', views.ProjectViewSet, basename='projects')
router.register('tasks', views.TaskViewSet, basename='tasks')

urlpatterns = router.urls
