from rest_framework import serializers

from testproject.testapp import models


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        exclude = ('project',)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Project
        fields = '__all__'

    task_set = TaskSerializer(many=True, source='task_set.all')
