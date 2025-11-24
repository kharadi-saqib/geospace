# #########################################################################
# #
# # Copyright (C) 2020 OSGeo
# #
# # This program is free software: you can redistribute it and/or modify
# # it under the terms of the GNU General Public License as published by
# # the Free Software Foundation, either version 3 of the License, or
# # (at your option) any later version.
# #
# # This program is distributed in the hope that it will be useful,
# # but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# # GNU General Public License for more details.
# #
# # You should have received a copy of the GNU General Public License
# # along with this program. If not, see <http://www.gnu.org/licenses/>.
# #
# #########################################################################

# from drf_spectacular.utils import extend_schema
# from pathlib import Path
# from dynamic_rest.viewsets import DynamicModelViewSet
# from dynamic_rest.filters import DynamicFilterBackend, DynamicSortingFilter

# from rest_framework.decorators import action
# from rest_framework.permissions import IsAuthenticatedOrReadOnly
# from geonode import settings

# from geonode.assets.utils import create_asset_and_link
# from geonode.base.api.filters import DynamicSearchFilter, ExtentFilter
# from geonode.base.api.mixins import AdvertisedListMixin
# from geonode.base.api.pagination import GeoNodeApiPagination
# from geonode.base.api.permissions import UserHasPerms
# from geonode.base.api.views import base_linked_resources, ApiPresetsInitializer
# from geonode.base import enumerations
# from geonode.documents.api.exceptions import DocumentException
# from geonode.documents.models import Document

# from geonode.base.api.serializers import ResourceBaseSerializer
# from geonode.resource.utils import resourcebase_post_save
# from geonode.storage.manager import StorageManager
# from geonode.resource.manager import resource_manager

# from .serializers import DocumentSerializer
# from .permissions import DocumentPermissionsFilter

# import logging


# logger = logging.getLogger(__name__)


# class DocumentViewSet(ApiPresetsInitializer, DynamicModelViewSet, AdvertisedListMixin):
#     """
#     API endpoint that allows documents to be viewed or edited.
#     """

#     http_method_names = ["get", "patch", "put", "post"]
#     permission_classes = [
#         IsAuthenticatedOrReadOnly,
#         UserHasPerms(perms_dict={"default": {"POST": ["base.add_resourcebase"]}}),
#     ]
#     filter_backends = [
#         DynamicFilterBackend,
#         DynamicSortingFilter,
#         DynamicSearchFilter,
#         ExtentFilter,
#         DocumentPermissionsFilter,
#     ]
#     queryset = Document.objects.all().order_by("-created")
#     serializer_class = DocumentSerializer
#     pagination_class = GeoNodeApiPagination

#     def perform_create(self, serializer):
#         """
#         Function to create document via API v2.
#         file_path: path to the file
#         doc_file: the open file

#         The API expect this kind of JSON:
#         {
#             "document": {
#                 "title": "New document",
#                 "metadata_only": true,
#                 "file_path": "/home/mattia/example.json"
#             }
#         }
#         File path rappresent the filepath where the file to upload is saved.

#         or can be also a form-data:
#         curl --location --request POST 'http://localhost:8000/api/v2/documents' \
#         --form 'title="Super Title2"' \
#         --form 'doc_file=@"/C:/Users/user/Pictures/BcMc-a6T9IM.jpg"' \
#         --form 'metadata_only="False"'
#         """
#         manager = None
#         serializer.is_valid(raise_exception=True)
#         file = serializer.validated_data.pop("file_path", None) or serializer.validated_data.pop("doc_file", None)
#         doc_url = serializer.validated_data.pop("doc_url", None)
#         extension = serializer.validated_data.pop("extension", None)

#         if not file and not doc_url:
#             raise DocumentException(detail="A file, file path or URL must be speficied")

#         if file and doc_url:
#             raise DocumentException(detail="Either a file or a URL must be specified, not both")

#         if not extension:
#             filename = file if isinstance(file, str) else file.name
#             extension = Path(filename).suffix.replace(".", "")

#         if extension not in settings.ALLOWED_DOCUMENT_TYPES:
#             raise DocumentException("The file provided is not in the supported extensions list")

#         try:
#             payload = {
#                 "owner": self.request.user,
#                 "extension": extension,
#                 "resource_type": "document",
#             }
#             if doc_url:
#                 payload["doc_url"] = doc_url
#                 payload["sourcetype"] = enumerations.SOURCE_TYPE_REMOTE

#             resource = serializer.save(**payload)

#             if file:
#                 manager = StorageManager(remote_files={"base_file": file})
#                 manager.clone_remote_files()
#                 create_asset_and_link(
#                     resource, self.request.user, [manager.get_retrieved_paths().get("base_file")], clone_files=True
#                 )
#                 manager.delete_retrieved_paths(force=True)

#             resource.set_missing_info()
#             resourcebase_post_save(resource.get_real_instance())
#             resource.set_default_permissions(owner=self.request.user, created=True)
#             resource.handle_moderated_uploads()
#             resource_manager.set_thumbnail(resource.uuid, instance=resource, overwrite=False)
#             return resource
#         except Exception as e:
#             logger.error(f"Error creating document {serializer.validated_data}", exc_info=e)
#             if manager:
#                 manager.delete_retrieved_paths()
#             raise e

#     @extend_schema(
#         methods=["get"],
#         responses={200: ResourceBaseSerializer(many=True)},
#         description="API endpoint allowing to retrieve linked resources",
#     )
#     @action(detail=True, methods=["get"])
#     def linked_resources(self, request, pk=None, *args, **kwargs):
#         return base_linked_resources(self.get_object().get_real_instance(), request.user, request.GET)
#########################################################################
#
# Copyright (C) 2020 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from drf_spectacular.utils import extend_schema
from pathlib import Path
from dynamic_rest.viewsets import DynamicModelViewSet
from dynamic_rest.filters import DynamicFilterBackend, DynamicSortingFilter

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from geonode import settings

from geonode.assets.utils import create_asset_and_link
from geonode.base.api.filters import DynamicSearchFilter, ExtentFilter
from geonode.base.api.mixins import AdvertisedListMixin
from geonode.base.api.pagination import GeoNodeApiPagination
from geonode.base.api.permissions import UserHasPerms
from geonode.base.api.views import base_linked_resources, ApiPresetsInitializer
from geonode.base import enumerations
from geonode.documents.api.exceptions import DocumentException
from geonode.documents.models import Document

from geonode.base.api.serializers import ResourceBaseSerializer
from geonode.resource.utils import resourcebase_post_save
from geonode.storage.manager import StorageManager
from geonode.resource.manager import resource_manager

from .serializers import DocumentSerializer
from .permissions import DocumentPermissionsFilter
from geonode.storage.manager import FileSystemStorageManager

import logging


logger = logging.getLogger(__name__)


# class DocumentViewSet(ApiPresetsInitializer, DynamicModelViewSet, AdvertisedListMixin):
#     """
#     API endpoint that allows documents to be viewed or edited.
#     """

#     http_method_names = ["get", "patch", "put", "post"]
#     permission_classes = [
#         IsAuthenticatedOrReadOnly,
#         UserHasPerms(perms_dict={"default": {"POST": ["base.add_resourcebase"]}}),
#     ]
#     filter_backends = [
#         DynamicFilterBackend,
#         DynamicSortingFilter,
#         DynamicSearchFilter,
#         ExtentFilter,
#         DocumentPermissionsFilter,
#     ]
#     queryset = Document.objects.all().order_by("-created")
#     serializer_class = DocumentSerializer
#     pagination_class = GeoNodeApiPagination

#     def perform_create(self, serializer):

#         print("\n========== DOCUMENT UPLOAD STARTED ==========")
#         """
#         Function to create document via API v2.
#         file_path: path to the file
#         doc_file: the open file

#         The API expect this kind of JSON:
#         {
#             "document": {
#                 "title": "New document",
#                 "metadata_only": true,
#                 "file_path": "/home/mattia/example.json"
#             }
#         }
#         File path rappresent the filepath where the file to upload is saved.

#         or can be also a form-data:
#         curl --location --request POST 'http://localhost:8000/api/v2/documents' \
#         --form 'title="Super Title2"' \
#         --form 'doc_file=@"/C:/Users/user/Pictures/BcMc-a6T9IM.jpg"' \
#         --form 'metadata_only="False"'
#         """
#         manager = None

#         print("Step 1: Validating serializer data...")
#         serializer.is_valid(raise_exception=True)
#         print("VALIDATED DATA:", serializer.validated_data)

#         # file = serializer.validated_data.pop("file_path", None) \
#         #     or serializer.validated_data.pop("doc_file", None)
#         # print("Step 2: FILE detected:", file)

#         uploaded_file = serializer.validated_data.pop("doc_file", None)
#         file_path = serializer.validated_data.pop("file_path", None)

#         if uploaded_file:
#             print("Uploaded file object:", uploaded_file, "TYPE:", type(uploaded_file))
#             file = uploaded_file
#         elif file_path:
#             print("File path provided:", file_path)
#             file = file_path
#         else:
#             file = None

#         print("FINAL FILE VALUE:", file, "TYPE:", type(file))

#         doc_url = serializer.validated_data.pop("doc_url", None)
#         print("Step 3: URL detected:", doc_url)

#         extension = serializer.validated_data.pop("extension", None)
#         print("Step 4: Initial EXTENSION:", extension)

#         # Error cases
#         if not file and not doc_url:
#             print("ERROR → No file or URL provided")
#             raise DocumentException("A file, file_path or URL must be specified")

#         if file and doc_url:
#             print("ERROR → Both file and URL provided")
#             raise DocumentException("Either a file or a URL must be specified, not both")

#         # Determine extension if missing
#         if not extension:
#             filename = file if isinstance(file, str) else file.name
#             extension = Path(filename).suffix.replace(".", "")
#             print("Step 5: Extracted EXTENSION:", extension)

#         print("Step 6: Checking extension is allowed:", settings.ALLOWED_DOCUMENT_TYPES)
#         if extension not in settings.ALLOWED_DOCUMENT_TYPES:
#             print("ERROR → Extension not allowed:", extension)
#             raise DocumentException("The file provided is not in the supported extensions list")

#         try:
#             print("Step 7: Preparing payload...")
#             payload = {
#                 "owner": self.request.user,
#                 "extension": extension,
#                 "resource_type": "document",
#             }
#             print("PAYLOAD:", payload)

#             if doc_url:
#                 payload["doc_url"] = doc_url
#                 payload["sourcetype"] = enumerations.SOURCE_TYPE_REMOTE
#                 print("Remote URL mode enabled")

#             print("Step 8: Saving serializer...")
#             resource = serializer.save(**payload)
#             print("RESOURCE CREATED:", resource)

#             if file:
#                 print("Step 9: Initializing StorageManager...")
#                 manager = StorageManager(
#                     remote_files={"base_file": file},
#                     concrete_storage_manager=FileSystemStorageManager(location=settings.MEDIA_ROOT),
#                 )
#                 print("StorageManager:", manager)

#                 print("Step 10: Cloning remote files...")
#                 manager.clone_remote_files()
#                 print("Cloned Files:", manager.clone_remote_files)

#                 retrieved = manager.get_retrieved_paths().get("base_file")
#                 print("Retrieved Paths:", retrieved)

#                 print("Step 11: Executing create_asset_and_link...")
#                 create_asset_and_link(
#                     resource, self.request.user, [retrieved], clone_files=True
#                 )
#                 print("Asset creation completed")

#                 print("Step 12: Deleting temporary retrieved files...")
#                 manager.delete_retrieved_paths(force=True)

#             print("Step 13: Post-processing resource...")
#             resource.set_missing_info()
#             print("Missing info set")

#             resourcebase_post_save(resource.get_real_instance())
#             print("Post-save hook executed")

#             resource.set_default_permissions(owner=self.request.user, created=True)
#             print("Default permissions set")

#             resource.handle_moderated_uploads()
#             print("Moderation handler executed")

#             print("Step 14: Setting thumbnail...")
#             resource_manager.set_thumbnail(resource.uuid, instance=resource, overwrite=False)

#             print("========== DOCUMENT UPLOAD SUCCESS ==========\n")
#             return resource

#         except Exception as e:
#             print("\n========== DOCUMENT UPLOAD FAILED ==========")
#             print("Exception:", str(e))
#             logger.error(f"Error creating document {serializer.validated_data}", exc_info=e)

#             if manager:
#                 print("Cleaning up retrieved files after error...")
#                 manager.delete_retrieved_paths()

#             print("=============================================\n")
#             raise e


class DocumentViewSet(ApiPresetsInitializer, DynamicModelViewSet, AdvertisedListMixin):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    http_method_names = ["get", "patch", "put", "post"]
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        UserHasPerms(perms_dict={"default": {"POST": ["base.add_resourcebase"]}}),
    ]
    filter_backends = [
        DynamicFilterBackend,
        DynamicSortingFilter,
        DynamicSearchFilter,
        ExtentFilter,
        DocumentPermissionsFilter,
    ]
    queryset = Document.objects.all().order_by("-created")
    serializer_class = DocumentSerializer
    pagination_class = GeoNodeApiPagination

    def perform_create(self, serializer):
        print("\n========== DOCUMENT UPLOAD STARTED ==========\n")

        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        uploaded_file = validated.pop("doc_file", None)
        file_path = validated.pop("file_path", None)
        doc_url = validated.pop("doc_url", None)

        print("STEP 1: uploaded_file =", uploaded_file)
        print("STEP 2: file_path =", file_path)
        print("STEP 3: doc_url =", doc_url)

        # CASE 1 — form-data uploaded file
        if uploaded_file:
            print("STEP 4: Handling LOCAL UPLOADED FILE (doc_file)")
            extension = Path(uploaded_file.name).suffix.replace(".", "")

            resource = serializer.save(
                owner=self.request.user,
                extension=extension,
                resource_type="document",
            )

            print("STEP 5: Saving uploaded_file directly to resource.doc_file")
            # resource.doc_file.save(uploaded_file.name, uploaded_file, save=True)

            print("STEP 6: File saved successfully, running final handlers")
            resource.set_missing_info()
            resourcebase_post_save(resource.get_real_instance())
            resource.set_default_permissions(owner=self.request.user, created=True)
            resource.handle_moderated_uploads()
            resource_manager.set_thumbnail(resource.uuid, instance=resource, overwrite=False)

            print("\n========== DOCUMENT UPLOAD SUCCESS ==========\n")
            return resource

        # CASE 2 — file_path on disk => use StorageManager
        if file_path:
            print("STEP X: Handling file_path using StorageManager")

            manager = StorageManager(
                remote_files={"base_file": file_path},
                concrete_storage_manager=FileSystemStorageManager(location=settings.MEDIA_ROOT),
            )
            manager.clone_remote_files()
            retrieved = manager.get_retrieved_paths()

            if not retrieved or not retrieved.get("base_file"):
                raise Exception("StorageManager did not return a valid local file")

            extension = Path(file_path).suffix.replace(".", "")

            resource = serializer.save(
                owner=self.request.user,
                extension=extension,
                resource_type="document",
            )

            print("STEP X: Linking asset")
            create_asset_and_link(
                resource,
                self.request.user,
                [retrieved["base_file"]],
                clone_files=True
            )

            manager.delete_retrieved_paths(force=True)

        # CASE 3 — remote URL => use StorageManager
        elif doc_url:
            print("STEP X: Handling doc_url via StorageManager")

            manager = StorageManager(remote_files={"base_file": doc_url})
            manager.clone_remote_files()
            retrieved = manager.get_retrieved_paths()

            if not retrieved or not retrieved.get("base_file"):
                raise Exception("StorageManager did not return a valid downloaded file")

            extension = Path(doc_url).suffix.replace(".", "")

            resource = serializer.save(
                owner=self.request.user,
                extension=extension,
                resource_type="document",
                sourcetype=enumerations.SOURCE_TYPE_REMOTE
            )

            create_asset_and_link(
                resource,
                self.request.user,
                [retrieved["base_file"]],
                clone_files=True
            )

            manager.delete_retrieved_paths(force=True)

        else:
            raise DocumentException("A file or URL must be provided")

        # COMMON FINAL HANDLERS
        resource.set_missing_info()
        resourcebase_post_save(resource.get_real_instance())
        resource.set_default_permissions(owner=self.request.user, created=True)
        resource.handle_moderated_uploads()
        resource_manager.set_thumbnail(resource.uuid, instance=resource, overwrite=False)

        print("\n========== DOCUMENT UPLOAD SUCCESS ==========\n")
        return resource


        # except Exception as e:
        #     print("\n========== DOCUMENT UPLOAD FAILED ==========\n")
        #     print("Exception:", e)

        #     if manager:
        #         print("Cleaning up retrieved files...")
        #         manager.delete_retrieved_paths(force=True)

        #     raise e


    @extend_schema(
        methods=["get"],
        responses={200: ResourceBaseSerializer(many=True)},
        description="API endpoint allowing to retrieve linked resources",
    )
    @action(detail=True, methods=["get"])
    def linked_resources(self, request, pk=None, *args, **kwargs):
        return base_linked_resources(self.get_object().get_real_instance(), request.user, request.GET)