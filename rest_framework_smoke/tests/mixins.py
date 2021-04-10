import random
from copy import deepcopy
from datetime import datetime, timedelta, date
from typing import (Optional, Union, List, cast, TYPE_CHECKING, Any, Type)
from urllib.parse import urlencode

import jsonschema
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import ForeignKey
from django.db.models.options import Options
from django.utils.datastructures import MultiValueDict
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from rest_framework.test import APITestCase
from rest_framework.utils import encoders

from rest_framework_smoke.tests import schemas

if TYPE_CHECKING:  # pragma: no cover
    MixinTarget = APITestCase
else:
    MixinTarget = object


class APIHelpersMixin(MixinTarget):
    # basename for `SimpleRouter.register()` call for tested viewset
    basename: str

    # viewset application label
    app_label: Optional[str] = None

    # object schema in list response
    schema: dict = {}

    # object schema in details response
    details_schema: dict = {}

    # json schema definition that describes pagination data in list response
    pagination_schema: Optional[dict] = schemas.PAGINATE_SCHEMA

    # object list key for paginated response
    page_result_key = 'results'

    # url path data name and corresponding model attribute name for
    # constructing detail url for object
    details_url_kwarg = details_url_field = 'pk'

    # attribute holding and object returned by tested viewset
    object_name: Optional[str] = None

    # primary key field name
    pk_field = 'id'

    # urls name format for tested viewset (see `url()` method)
    url_name_format = '{basename}-{suffix}'

    # client authentication is performed in API
    authentication: bool = True

    # list of fields that can't be updated via API
    read_only_update_fields = ()

    @property
    def obj(self) -> models.Model:
        return getattr(self, cast(str, self.object_name))

    @property
    def model(self) -> Type[models.Model]:
        return self.obj._meta.model

    @property
    def object_list(self) -> List[models.Model]:
        return [self.obj]

    def url(self, suffix: str, *, version: Optional[str] = None,
            query: Union[None, dict, MultiValueDict] = None,
            **kwargs: Any) -> str:
        """
        Constructs an url for viewset

        :param suffix: last part of viewset url (list/detail or action name)
        :param version: API version
        :param query: query parameters for a link
        :param kwargs: url data for reversing
        """
        name = self.url_name_format.format(
            version=version,
            app_label=self.app_label,
            basename=self.basename,
            suffix=suffix,
        )
        url = reverse(name, kwargs=kwargs)

        # support multiple values for same param: "id=1&id=2&id=3"
        if isinstance(query, MultiValueDict):
            params = []
            for key, value in query.lists():
                if isinstance(value, list):
                    params.append('&'.join([f'{key}={x}' for x in value]))
                else:
                    params.append(f'{key}={value}')

            url += f"?{'&'.join(params)}"
        elif query:
            # simple dict query params
            url += '?%s' % urlencode(query)
        return url

    @staticmethod
    def maybe_json(response: Response) -> Union[None, list, dict]:
        if response.status_code == HTTP_204_NO_CONTENT:
            return None
        return response.json()

    @staticmethod
    def clone_object(obj: models.Model, **kwargs) -> models.Model:
        """ Clones a django model instance."""
        obj = deepcopy(obj)
        obj.pk = None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.save(force_insert=True)
        return obj

    def change_value(self, obj: models.Model, field: str) -> Any:
        opts: Options = obj._meta
        try:
            f = opts.get_field(field)
            if isinstance(f, ForeignKey):
                related = getattr(obj, field)
                return self.clone_object(related).pk
        except FieldDoesNotExist:
            pass
        value = getattr(obj, field)
        if isinstance(value, bool):
            return not value
        if isinstance(value, int):
            return value + 1
        if isinstance(value, float):
            return value + 0.1
        if isinstance(value, str):
            return value + 'N'
        if isinstance(value, datetime):
            return value + timedelta(seconds=1)
        if isinstance(value, date):
            return value + timedelta(days=1)
        raise TypeError(value, field)

    def perform_request(self, suffix: str, detail: bool, *,
                        method: str = 'GET',
                        headers: Optional[dict] = None,
                        status: int = HTTP_200_OK,
                        data: Optional[dict] = None,
                        **kwargs: Any) -> Response:
        """
        Requests viewset endpoint.

        :param suffix: suffix for endpoint url to request
        :param detail: flag for injecting details_url_kwarg to url
        :param method: HTTP method used in request
        :param headers: http headers dict
        :param status: expected response status
        :param data: request body data
        :param kwargs: url reversing parameters
        """
        headers = headers or {}
        if detail and not kwargs:
            kwargs = self.get_detail_url_kwargs(self.obj)
        url = self.url(suffix, **kwargs)
        if data is not None:
            headers['content_type'] = 'application/json'
        body = encoders.JSONEncoder().encode(data)
        r = cast(Response, self.client.generic(method, url,
                                               data=body,
                                               **headers))
        self.assertEqual(r.status_code, status, self.maybe_json(r))
        return r

    def get_detail_url_kwargs(self, obj: models.Model) -> dict:
        value = getattr(obj, self.details_url_field)
        return {self.details_url_kwarg: value}

    def get_list(self, headers: Optional[dict] = None,
                 status: int = HTTP_200_OK, **kwargs: Any) -> List[dict]:
        """
        Returns list of object retrieved through api.

        If pagination_schema is set, strips pagination info from response
        """
        r = self.perform_request('list', False, headers=headers,
                                 status=status, **kwargs)
        data = r.json()
        if self.pagination_schema:
            return data.get(self.page_result_key, data)
        else:
            return data

    def get_detail(self, *, suffix: str = 'detail', status: int = HTTP_200_OK,
                   headers: Optional[dict] = None, **kwargs: Any) -> dict:
        """ Returns object details retrieved through api."""
        r = self.perform_request(suffix, True, headers=headers, status=status,
                                 **kwargs)
        return r.json()

    def perform_create(self, data: dict,
                       status: int = HTTP_201_CREATED) -> dict:
        """ Returns object details created via api."""
        r = self.perform_request('list', False, method='POST',
                                 status=status, data=data)
        return r.json()

    def perform_update(self, data: dict, partial: bool = False,
                       status: int = HTTP_200_OK, **kwargs) -> dict:
        """ Returns details for an object updated via api."""
        method = 'PATCH' if partial else 'PUT'
        r = self.perform_request('detail', False, method=method,
                                 status=status, data=data, **kwargs)
        return r.json()

    def perform_delete(self, *, status: int = HTTP_204_NO_CONTENT, **kwargs
                       ) -> Optional[dict]:
        """ Performs an object deletion via api."""
        r = self.perform_request('detail', False, method='DELETE',
                                 status=status, **kwargs)
        return self.maybe_json(r)
    
    def delete(self, status: int = HTTP_204_NO_CONTENT,
               obj: Optional[models.Model] = None
               ) -> Optional[dict]:
        """ Deletes current object via api."""
        if obj is None:
            obj = self.obj
        kwargs = self.get_detail_url_kwargs(obj)
        return self.perform_delete(status=status, **kwargs)

    def create(self, data: Optional[dict] = None,
               status: int = HTTP_201_CREATED) -> dict:
        """
        Created a new object via API.

        If kwargs not specified, deletes current object from db and uses it's
        details to create a copy via API.

        :param data: new object data
        :param status: expected response status
        :return: response data
        """
        if data is None:
            data = self.get_detail()
            self.obj.delete()
            del data[self.pk_field]

        return self.perform_create(data, status=status)

    def update(self,
               obj: Optional[models.Model] = None,
               data: Optional[dict] = None,
               partial: bool = False,
               status: int = HTTP_200_OK) -> dict:
        """
        Updates an object with passed data via API.
        By default, uses self.obj
        If data not passed, tries to change every field in object details
        except pk field.

        :param obj: object to be updated
        :param data: update data
        :param partial: partial update flag
        :param status: expected response status
        """
        if obj is None:
            obj = self.obj
        kwargs = self.get_detail_url_kwargs(obj)
        read_only = self.read_only_update_fields
        if data is None:
            data = self.get_detail(**kwargs)
            del data[self.pk_field]
            for k in data:
                if k in read_only:
                    continue
                data[k] = self.change_value(obj, k)
            if partial:
                key = random.choice([f for f in data if f not in read_only])
                data = {key: data[key]}
        return self.perform_update(data, status=status, partial=partial,
                                   **kwargs)

    def get_schema(self) -> dict:
        """ Returns object schema for list response.
        """
        return schemas.get_object_schema(self.schema)

    def get_details_schema(self, attr='details_schema') -> dict:
        """ Returns object schema for details response."""
        return schemas.get_object_schema(getattr(self, attr))

    def get_list_schema(self, min_items: int = 1) -> dict:
        """ Returns list response schema with pagination data
        """
        result_list_schema = {
            "type": "array",
            "items": self.get_schema(),
            "minItems": min_items}
        if not self.pagination_schema:
            return result_list_schema

        schema = self.pagination_schema
        schema.update({"results": result_list_schema})
        return schema

    def assert_json_schema(self, obj: dict, schema: dict) -> None:
        """ Checks response schema."""
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:  # pragma: no cover
            self.fail(e.message)

    def assert_object_list(self, objects: List[models.Model],
                           **kwargs: Any) -> None:
        """
        Requests object list and checks primary key lists with expected object
        list.
        """
        data = self.get_list(**kwargs)
        ids = [obj[self.pk_field] for obj in data]
        expected = [obj.pk for obj in objects]
        self.assertListEqual(ids, expected)


if TYPE_CHECKING:  # pragma: no cover
    APIHelpersTarget = APIHelpersMixin
else:
    APIHelpersTarget = object


class ListTestsMixin(APIHelpersTarget):

    def test_list_format(self) -> None:
        """ Checks list response format."""
        r = self.perform_request('list', False)
        self.assert_json_schema(r.json(), self.get_list_schema())

    def test_list_default_filters(self):
        """ API outputs all objects from db."""
        self.assert_object_list(self.model.objects.all())

    def test_object_list_smoke(self) -> None:
        """ Check that object list API returns an object list."""
        self.assert_object_list(self.object_list)

    def test_authorization(self) -> None:
        """ Checks client authorization."""
        r = self.perform_request('list', False)
        if self.authentication:
            self.assertFalse(r.wsgi_request.user.is_anonymous)
        else:
            self.assertTrue(r.wsgi_request.user.is_anonymous)


class DetailTestsMixin(APIHelpersTarget):

    def test_detail_format(self) -> None:
        """ Checks detail response format."""
        r = self.perform_request('detail', True)
        self.assert_json_schema(r.json(), self.get_details_schema())

    def test_retrieve_object_smoke(self) -> None:
        """ Check that object detail API returns an object."""
        obj = self.get_detail()
        self.assertEqual(obj[self.pk_field], self.obj.pk)

    def test_authorization(self) -> None:
        """ Checks client authorization."""
        r = self.perform_request('detail', True)
        if self.authentication:
            self.assertFalse(r.wsgi_request.user.is_anonymous)
        else:
            self.assertTrue(r.wsgi_request.user.is_anonymous)


class ReadViewSetTestsMixin(ListTestsMixin, DetailTestsMixin, APIHelpersMixin):
    """ Tests for read API ViewSets: list + retrieve."""


class ReadOnlyViewSetTestsMixin(ReadViewSetTestsMixin):
    """ Tests for read-only API ViewSets (write not allowed)."""

    def test_create_not_allowed(self):
        """ Object creation is not allowed."""
        self.perform_request('list', False, method='POST',
                             status=HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        """ Object update is not allowed."""
        for method in ('PUT', 'PATCH'):
            with self.subTest(method):
                self.perform_request('detail', True, method=method,
                                     status=HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        """ Object deletion is not allowed."""
        self.perform_request('detail', True, method='DELETE',
                             status=HTTP_405_METHOD_NOT_ALLOWED)


class CreateViewSetTestsMixin(APIHelpersMixin):
    """ Tests for create method in API ViewSet."""

    def test_create_format(self):
        """ Checks create API response format."""
        data = self.create()
        self.assert_json_schema(data, self.get_details_schema())

    def test_create_object_smoke(self) -> models.Model:
        """ Checks that object is created via API."""
        data = self.create()

        pk = data[self.pk_field]
        obj = self.model.objects.filter(pk=pk).first()
        self.assertIsNotNone(obj)
        return obj


class DeleteViewSetTestsMixin(APIHelpersMixin):
    """ Tests for delete method in API ViewSet."""

    def test_delete_object_smoke(self):
        """ Checks that object is deleted via API."""
        self.delete()


class FullUpdateViewSetTestsMixin(APIHelpersMixin):
    """ Tests for full update in API ViewSet."""

    def test_full_update_format(self):
        """ Checks PUT response format."""
        data = self.update()
        self.assert_json_schema(data, self.get_details_schema())

    def test_full_update_smoke(self):
        """ Checks that object can be updated via API."""
        previous = self.get_detail()
        data = self.update()
        for k in data:
            if k == self.pk_field or k in self.read_only_update_fields:
                continue
            self.assertNotEqual(previous[k], data[k])


class PartialUpdateViewSetTestsMixin(APIHelpersMixin):
    """ Tests for partial update in API ViewSet."""

    def test_partial_update_format(self):
        """ Checks PATCH response format."""
        previous = self.get_detail()
        read_only = [self.pk_field] + list(self.read_only_update_fields)
        key = random.choice([f for f in previous if f not in read_only])
        patch = {key: self.change_value(self.obj, key)}

        data = self.update(data=patch, partial=True)
        for k in data:
            if k == key:
                self.assertNotEqual(previous[k], data[k], k)
            else:
                self.assertEqual(previous[k], data[k], k)

    def test_partial_update_smoke(self):
        """ Checks that object can be updated via API."""
        previous = self.get_detail()
        data = self.update(partial=True)
        self.assertNotEqual(previous, data)


class UpdateViewSetTestsMixin(FullUpdateViewSetTestsMixin,
                              PartialUpdateViewSetTestsMixin):
    """ Tests for full and partial update API."""
