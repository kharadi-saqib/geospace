#########################################################################
#
# Copyright (C) 2021 OSGeo
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
import logging
from urllib.parse import urljoin, urlsplit
from django.conf import settings
from django.http import Http404, HttpResponse
from django.urls import reverse
from geonode.resource.enumerator import ExecutionRequestAction
from django.utils.translation import gettext_lazy as _
from dynamic_rest.filters import DynamicFilterBackend, DynamicSortingFilter
from dynamic_rest.viewsets import DynamicModelViewSet
from geonode.base.api.filters import DynamicSearchFilter, ExtentFilter, FavoriteFilter
from geonode.base.api.pagination import GeoNodeApiPagination
from geonode.base.api.permissions import (
    IsSelfOrAdminOrReadOnly,
    ResourceBasePermissionsFilter,
    UserHasPerms,
)
from rest_framework.exceptions import ValidationError
from rest_framework import status
from geonode.base.api.serializers import ResourceBaseSerializer
from geonode.base.api.views import ResourceBaseViewSet
from geonode.base.models import ResourceBase
from geonode.storage.manager import StorageManager
from geonode.upload.api.permissions import UploadPermissionsFilter
from geonode.upload.models import UploadParallelismLimit, UploadSizeLimit
from geonode.upload.utils import UploadLimitValidator
from geonode.upload.api.exceptions import HandlerException, ImportException
from geonode.upload.api.serializer import ImporterSerializer
from geonode.upload.celery_tasks import import_orchestrator
from geonode.upload.orchestrator import orchestrator
from rest_framework.parsers import FileUploadParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from geonode.proxy.utils import proxy_urls_registry
from geonode.storage.manager import FileSystemStorageManager
from geonode.upload.celery_tasks import import_orchestrator
import os
import glob
import zipfile
from pathlib import Path, PosixPath
import logging
from geonode.upload.api.serializer import (
    UploadParallelismLimitSerializer,
    UploadSizeLimitSerializer,
)
logger = logging.getLogger(__name__)
logger = logging.getLogger("importer")


class UploadSizeLimitViewSet(DynamicModelViewSet):
    http_method_names = ["get", "post"]
    permission_classes = [IsSelfOrAdminOrReadOnly]
    queryset = UploadSizeLimit.objects.all()
    serializer_class = UploadSizeLimitSerializer
    pagination_class = GeoNodeApiPagination

    def destroy(self, request, *args, **kwargs):
        protected_objects = [
            "dataset_upload_size",
            "document_upload_size",
            "file_upload_handler",
        ]
        instance = self.get_object()
        if instance.slug in protected_objects:
            detail = _(f"The limit `{instance.slug}` should not be deleted.")
            raise ValidationError(detail)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadParallelismLimitViewSet(DynamicModelViewSet):
    http_method_names = ["get", "post"]
    permission_classes = [IsSelfOrAdminOrReadOnly]
    queryset = UploadParallelismLimit.objects.all()
    serializer_class = UploadParallelismLimitSerializer
    pagination_class = GeoNodeApiPagination

    def get_serializer(self, *args, **kwargs):
        serializer = super(UploadParallelismLimitViewSet, self).get_serializer(*args, **kwargs)
        if self.action == "create":
            serializer.fields["slug"].read_only = False
        return serializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.slug == "default_max_parallel_uploads":
            detail = _("The limit `default_max_parallel_uploads` should not be deleted.")
            raise ValidationError(detail)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


from pathlib import Path, PosixPath
import os
import zipfile
import glob


class ImporterViewSet(DynamicModelViewSet):

    parser_class = [JSONParser, FileUploadParser, MultiPartParser]
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        UserHasPerms(perms_dict={"default": {"POST": ["base.add_resourcebase"]}}),
    ]
    filter_backends = [
        DynamicFilterBackend,
        DynamicSortingFilter,
        DynamicSearchFilter,
        UploadPermissionsFilter,
    ]
    queryset = ResourceBase.objects.all().order_by("-last_updated")
    serializer_class = ImporterSerializer
    pagination_class = GeoNodeApiPagination
    http_method_names = ["get", "post"]

    def get_serializer_class(self):
        specific_serializer = orchestrator.get_serializer(self.request.data)
        return specific_serializer or ImporterSerializer

    # ------------------------------------------------------------------------
    # FINAL MERGED CREATE()
    # ------------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        print("FILES:", request.FILES)
        print("DATA:", request.data)

        # 1) detect uploaded file
        _file = (
            request.FILES.get("base_file")
            or request.FILES.get("upload")
            or request.FILES.get("file")
            or request.FILES.get("files")
        )
        if not _file:
            raise ImportException("No upload file received")

        execution_id = None
        storage_manager = None

        # serializer validation
        serializer_cls = self.get_serializer_class()
        serializer = serializer_cls(data=request.data)
        serializer.is_valid(raise_exception=True)

        # initial payload merging
        _data = {
            **serializer.data.copy(),
            **{k: (v[0] if isinstance(v, list) else v) for k, v in request.FILES.items()},
        }
        # remove legacy keys and set required fields...
        for bad_key in ("tif_file", "tiff_file"):
            if bad_key in _data:
                del _data[bad_key]
        _data["store"] = "datastore"
        _data["workspace"] = "geonode"

        is_shapefile_zip = getattr(_file, "name", "").lower().endswith(".zip")

        # Prepare remote_files
        remote_files = {}
        if "base_file" in _data:
            remote_files["base_file"] = _data["base_file"]
        for key in ("shp_file", "dbf_file", "shx_file", "prj_file"):
            if key in _data:
                remote_files[key] = _data[key]

        storage_manager = StorageManager(
            remote_files=remote_files,
            concrete_storage_manager=FileSystemStorageManager(location=settings.MEDIA_ROOT),
        )

        # clone into temp dir — important: capture retrieved_paths
        retrieved_paths = storage_manager.clone_remote_files(create_tempdir=True, unzip=False)
        print("Retrieved paths:", retrieved_paths)

        # --- MERGE retrieved paths FIRST (so they are available) ---
        _data |= storage_manager.get_retrieved_paths()

        # If ZIP, extract SHP files and THEN override base_file to be the .shp
        if is_shapefile_zip:
            print("Extracting shapefile ZIP...")
            zip_path = storage_manager.get_retrieved_paths().get("base_file")
            zip_path = str(zip_path)
            if not os.path.isfile(zip_path):
                raise ImportException("Uploaded ZIP not found after cloning")

            extract_dir = zip_path.rsplit(".zip", 1)[0]
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)

            shp = glob.glob(os.path.join(extract_dir, "*.shp"))
            dbf = glob.glob(os.path.join(extract_dir, "*.dbf"))
            shx = glob.glob(os.path.join(extract_dir, "*.shx"))
            prj = glob.glob(os.path.join(extract_dir, "*.prj"))

            if not (shp and dbf and shx):
                raise ImportException("Missing required SHP components (.shp .dbf .shx)")

            # IMPORTANT: override base_file to point to the .shp file (what ShapeFileHandler expects)
            _data["base_file"] = str(shp[0])
            _data["shp_file"] = str(shp[0])
            _data["dbf_file"] = str(dbf[0])
            _data["shx_file"] = str(shx[0])
            if prj:
                _data["prj_file"] = str(prj[0])

            # keep a reference to the original uploaded zip (some logic expects zip_file)
            _data["zip_file"] = str(retrieved_paths.get("base_file"))

        # Now validate upload limits
        self.validate_upload(request, storage_manager)

        # Convert any Path/PosixPath to str
        for k, v in list(_data.items()):
            if isinstance(v, (Path, PosixPath)):
                _data[k] = str(v)

        # Remove keys that confuse handler detection (but DO NOT remove zip_file)
        # --------------------------------------
# Remove keys that confuse handler detection
# --------------------------------------
        for bad in ("files", "tif_file", "tiff_file"):
            if bad in _data:
                print(f"⚠️ Removing invalid key: {bad}")
                del _data[bad]

        # 🔥 CRITICAL FIX: REMOVE zip_file so handler switches to SHP mode
        if "zip_file" in _data:
            print("🔥 Removing zip_file to enable ShapeFileHandler (SHP mode)")
            del _data["zip_file"]


        # proceed with handler detection and rest of flow...
        handler = orchestrator.get_handler(_data)
        action = _data.get("action")
        if not handler or not handler.can_do(action):
            raise ImportException("No handler found for this file type")

        # extract params, build files_dict (dict, not list)
        extracted_params, _handler_files = handler.extract_params_from_data(_data)
        if "files" in extracted_params:
            del extracted_params["files"]
        for k, v in extracted_params.items():
            if isinstance(v, (Path, PosixPath)):
                extracted_params[k] = str(v)

        files_dict = {}
        if "base_file" in _data:
            files_dict["base_file"] = _data["base_file"]
        for comp in ("shp_file", "dbf_file", "shx_file", "prj_file"):
            if comp in _data:
                files_dict[comp] = _data[comp]
        files_dict = {k: (str(v) if isinstance(v, (Path, PosixPath)) else v) for k, v in files_dict.items()}

        input_params = {
            "files": files_dict,
            "temporary_files": files_dict,
            "handler_module_path": str(handler),
            **extracted_params,
        }

        execution_id = orchestrator.create_execution_request(
            user=request.user,
            func_name=next(iter(handler.get_task_list(action))),
            step=_(next(iter(handler.get_task_list(action)))),
            input_params=input_params,
            action=action,
            resource=extracted_params.get("resource_pk"),
            name=getattr(_file, "name", None),
        )

        try:
            result = import_orchestrator(_data, str(execution_id), handler=str(handler), action=action)
            return Response({"execution_id": execution_id, "result": result}, status=201)
        except Exception as e:
            if storage_manager:
                try:
                    storage_manager.delete_retrieved_paths(force=True)
                except Exception:
                    pass
            orchestrator.set_as_failed(execution_id=str(execution_id), reason=e)
            raise ImportException(detail=str(e))


    # -------------------------------------------------------------------
    def validate_upload(self, request, storage_manager):
        upload_validator = UploadLimitValidator(request.user)
        upload_validator.validate_parallelism_limit_per_user()
        upload_validator.validate_files_sum_of_sizes(storage_manager.data_retriever)

class ResourceImporter(DynamicModelViewSet):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        UserHasPerms(
            perms_dict={
                "dataset": {
                    "PUT": ["base.add_resourcebase", "base.download_resourcebase"],
                    "rule": all,
                },
                "document": {
                    "PUT": ["base.add_resourcebase", "base.download_resourcebase"],
                    "rule": all,
                },
                "default": {"PUT": ["base.add_resourcebase"]},
            }
        ),
    ]
    filter_backends = [
        DynamicFilterBackend,
        DynamicSortingFilter,
        DynamicSearchFilter,
        ExtentFilter,
        ResourceBasePermissionsFilter,
        FavoriteFilter,
    ]
    queryset = ResourceBase.objects.all().order_by("-last_updated")
    serializer_class = ResourceBaseSerializer
    pagination_class = GeoNodeApiPagination

    def copy(self, request, *args, **kwargs):
        try:
            resource = self.get_object()
            if resource.resourcehandlerinfo_set.exists():
                handler_module_path = resource.resourcehandlerinfo_set.first().handler_module_path

                action = ExecutionRequestAction.COPY.value

                handler = orchestrator.load_handler(handler_module_path)

                if not handler.can_do(action):
                    raise HandlerException(
                        detail=f"The handler {handler_module_path} cannot manage the action required: {action}"
                    )

                step = next(iter(handler.get_task_list(action=action)))

                extracted_params, _data = handler.extract_params_from_data(request.data, action=action)

                execution_id = orchestrator.create_execution_request(
                    user=request.user,
                    func_name=step,
                    step=step,
                    action=action,
                    input_params={
                        **{"handler_module_path": handler_module_path},
                        **extracted_params,
                    },
                )

                sig = import_orchestrator.s(
                    {},
                    str(execution_id),
                    step=step,
                    handler=str(handler_module_path),
                    action=action,
                    layer_name=resource.title,
                    alternate=resource.alternate,
                )
                sig.apply_async()

                # to reduce the work on the FE, the old payload is mantained
                return Response(
                    data={
                        "status": "ready",
                        "execution_id": execution_id,
                        "status_url": urljoin(
                            settings.SITEURL,
                            reverse("rs-execution-status", kwargs={"execution_id": execution_id}),
                        ),
                    },
                    status=200,
                )
        except (Exception, Http404) as e:
            logger.error(e)
            return HttpResponse(status=404, content=e)
        return ResourceBaseViewSet(request=request, format_kwarg=None, args=args, kwargs=kwargs).resource_service_copy(
            request, pk=kwargs.get("pk")
        )
