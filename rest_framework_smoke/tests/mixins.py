from typing import (Optional, Union, List, cast, TYPE_CHECKING, Any)
from urllib.parse import urlencode

import jsonschema
from django.db import models
from django.utils.datastructures import MultiValueDict
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

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

    # url path kwargs name and corresponding model attribute name for
    # constructing detail url for object
    details_url_kwarg = details_url_field = 'pk'

    # attribute holding and object returned by tested viewset
    object_name: Optional[str] = None

    # primary key field name
    pk_field = 'id'

    # urls name format for tested viewset (see `url()` method)
    url_name_format = '{basename}-{suffix}'

    @property
    def obj(self) -> models.Model:
        return getattr(self, cast(str, self.object_name))

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
        :param kwargs: url kwargs for reversing
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

    def perform_request(self, suffix: str, detail: bool, *,
                        headers: Optional[dict] = None, status: int = 200,
                        **kwargs: Any) -> Response:
        """
        Requests viewset endpoint.

        :param suffix: suffix for endpoint url to request.
        :param detail: flag for injecting details_url_kwarg to url
        :param headers: http headers dict
        :param status: expected response status
        :param kwargs: url reversing parameters
        """
        headers = headers or {}
        if detail and not kwargs:
            value = getattr(self.obj, self.details_url_field)
            kwargs.setdefault(self.details_url_kwarg, value)
        r = self.client.get(self.url(suffix, **kwargs), **headers)
        self.assertEqual(r.status_code, status)
        return r

    def get_list(self, headers: Optional[dict] = None, status: int = 200,
                 **kwargs: Any) -> List[dict]:
        """
        Returns list of object retrieved through api.

        If pagination_schema is set, strips pagination info from response
        """
        r = self.perform_request('list', False, headers=headers,
                                 status=status, **kwargs)
        data = r.json()
        if self.pagination_schema:
            return data[self.page_result_key]
        else:
            return data

    def get_detail(self, *, suffix: str = 'detail', status: int = 200,
                   headers: Optional[dict] = None, **kwargs: Any) -> dict:
        """ Returns object details retrieved through api."""
        r = self.perform_request(suffix, True, headers=headers, status=status,
                                 **kwargs)
        return r.json()

    def get_schema(self) -> dict:
        """ Returns object schema for list response.
        """
        return schemas.get_object_schema(self.schema)

    def get_details_schema(self) -> dict:
        """ Returns object schema for details response."""
        return schemas.get_object_schema(self.details_schema)

    def get_list_schema(self, min_items: int = 1) -> dict:
        """ Returns list response schema with pagination data
        """
        result_list_schema = {
            "type": ["array"],
            "items": self.get_schema(),
            "minItems": min_items}
        if not self.pagination_schema:
            return result_list_schema

        schema = self.pagination_schema
        schema.update({"results": result_list_schema})
        return schemas.get_object_schema(schema)

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
        r = self.perform_request('list', False,
                                 query={'limit': 1, 'offset': 1})
        self.assert_json_schema(r.json(), self.get_list_schema())


class DetailTestsMixin(APIHelpersTarget):

    def test_detail_format(self) -> None:
        """ Checks detail response format."""
        r = self.perform_request('detail', True)
        self.assert_json_schema(r.json(), self.get_details_schema())


class ReadOnlyViewSetTestsMixin(ListTestsMixin, DetailTestsMixin,
                                APIHelpersMixin):
    """ Tests for readonly API ViewSets: list + retrieve."""
