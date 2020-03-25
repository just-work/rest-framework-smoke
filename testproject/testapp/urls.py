from rest_framework.routers import SimpleRouter

from testproject.testapp import views

router = SimpleRouter()

router.register('projects', views.ProjectViewSet, basename='projects')

urlpatterns = router.urls
