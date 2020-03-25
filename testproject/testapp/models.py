from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=32)


class Task(models.Model):
    project = models.ForeignKey(Project, models.CASCADE)
    name = models.CharField(max_length=32)
