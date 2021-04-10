from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from testproject.testapp import models, serializers


class ProjectViewSet(ReadOnlyModelViewSet):
    queryset = models.Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    pagination_class = None
    permission_classes = []

    @action(detail=True)
    def ping(self, request, pk):
        models.Project.objects.filter(pk=pk).update(name='ping')
        return Response(status=201)

    @action(detail=False)
    def first(self, request):
        project = models.Project.objects.first()
        serializer = self.get_serializer(instance=project)
        return Response(serializer.data)


class TaskViewSet(ModelViewSet):
    queryset = models.Task.objects.order_by('name')
    serializer_class = serializers.TaskSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return serializers.TaskUpdateSerializer
        return self.serializer_class

    def perform_update(self, serializer: BaseSerializer) -> None:
        super().perform_update(serializer)
    
    


