from rest_framework import serializers

from testproject.testapp import models


class ProjectTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        exclude = ('project',)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Project
        fields = '__all__'

    task_set = ProjectTaskSerializer(many=True, source='task_set.all')


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        fields = '__all__'


class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        read_only_fields = ['project']
        fields = '__all__'
