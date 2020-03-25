from rest_framework import pagination, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from testproject.testapp import models, serializers


class ProjectViewSet(ModelViewSet):
    queryset = models.Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    pagination_class = pagination.LimitOffsetPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True)
    def ping(self, request, pk):
        models.Project.objects.filter(pk=pk).update(name='ping')
        return Response(status=201)

    @action(detail=False)
    def first(self, request):
        project = models.Project.objects.first()
        serializer = self.get_serializer(instance=project)
        return Response(serializer.data)
