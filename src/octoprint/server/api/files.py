# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import hashlib
import logging
import os
import threading

import psutil
from flask import jsonify, make_response, request, url_for

import octoprint.filemanager
import octoprint.filemanager.storage
import octoprint.filemanager.util
import octoprint.slicing
from octoprint.access.permissions import Permissions
from octoprint.events import Events
from octoprint.filemanager.destinations import FileDestinations
from octoprint.server import (
    NO_CONTENT,
    current_user,
    eventManager,
    fileManager,
    printer,
    slicingManager,
)
from octoprint.server.api import api
from octoprint.server.util.flask import (
    get_json_command_from_request,
    no_firstrun_access,
    with_revalidation_checking,
)
from octoprint.settings import settings, valid_boolean_trues
from octoprint.util import sv, time_this

# ~~ GCODE file handling

_file_cache = {}
_file_cache_mutex = threading.RLock()

_DATA_FORMAT_VERSION = "v2"


def _clear_file_cache():
    with _file_cache_mutex:
        _file_cache.clear()


def _create_lastmodified(path, recursive):
    path = path[len("/api/files") :]
    if path.startswith("/"):
        path = path[1:]

    if path == "":
        # all storages involved
        lms = [0]
        for storage in fileManager.registered_storages:
            try:
                lms.append(fileManager.last_modified(storage, recursive=recursive))
            except Exception:
                logging.getLogger(__name__).exception(
                    "There was an error retrieving the last modified data from storage {}".format(
                        storage
                    )
                )
                lms.append(None)

        if any(filter(lambda x: x is None, lms)):
            # we return None if ANY of the involved storages returned None
            return None

        # if we reach this point, we return the maximum of all dates
        return max(lms)

    else:
        if "/" in path:
            storage, path_in_storage = path.split("/", 1)
        else:
            storage = path
            path_in_storage = None

        try:
            return fileManager.last_modified(
                storage, path=path_in_storage, recursive=recursive
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "There was an error retrieving the last modified data from storage {} and path {}".format(
                    storage, path_in_storage
                )
            )
            return None


def _create_etag(path, filter, recursive, lm=None):
    if lm is None:
        lm = _create_lastmodified(path, recursive)

    if lm is None:
        return None

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))
    hash_update(str(filter))
    hash_update(str(recursive))

    path = path[len("/api/files") :]
    if path.startswith("/"):
        path = path[1:]

    if "/" in path:
        storage, _ = path.split("/", 1)
    else:
        storage = path

    if path == "" or storage == FileDestinations.SDCARD:
        # include sd data in etag
        hash_update(repr(sorted(printer.get_sd_files(), key=lambda x: sv(x["name"]))))

    hash_update(_DATA_FORMAT_VERSION)  # increment version if we change the API format

    return hash.hexdigest()


@api.route("/files", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        request.values.get("filter", False),
        request.values.get("recursive", False),
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(
        request.path, request.values.get("recursive", False)
    ),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFiles():
    filter = request.values.get("filter", False)
    recursive = request.values.get("recursive", "false") in valid_boolean_trues
    force = request.values.get("force", "false") in valid_boolean_trues

    files = _getFileList(
        FileDestinations.LOCAL,
        filter=filter,
        recursive=recursive,
        allow_from_cache=not force,
    )
    files.extend(_getFileList(FileDestinations.SDCARD))

    usage = psutil.disk_usage(settings().getBaseFolder("uploads", check_writable=False))
    return jsonify(files=files, free=usage.free, total=usage.total)


@api.route("/files/<string:origin>", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        request.values.get("filter", False),
        request.values.get("recursive", False),
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(
        request.path, request.values.get("recursive", False)
    ),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFilesForOrigin(origin):
    if origin not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
        return make_response("Unknown origin: %s" % origin, 404)

    filter = request.values.get("filter", False)
    recursive = request.values.get("recursive", "false") in valid_boolean_trues
    force = request.values.get("force", "false") in valid_boolean_trues

    files = _getFileList(
        origin, filter=filter, recursive=recursive, allow_from_cache=not force
    )

    if origin == FileDestinations.LOCAL:
        usage = psutil.disk_usage(
            settings().getBaseFolder("uploads", check_writable=False)
        )
        return jsonify(files=files, free=usage.free, total=usage.total)
    else:
        return jsonify(files=files)


@api.route("/files/<string:target>/<path:filename>", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        request.values.get("filter", False),
        request.values.get("recursive", False),
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(
        request.path, request.values.get("recursive", False)
    ),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFile(target, filename):
    if target not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
        return make_response("Unknown target: %s" % target, 404)

    recursive = False
    if "recursive" in request.values:
        recursive = request.values["recursive"] in valid_boolean_trues

    file = _getFileDetails(target, filename, recursive=recursive)
    if not file:
        return make_response("File not found on '%s': %s" % (target, filename), 404)

    return jsonify(file)


def _getFileDetails(origin, path, recursive=True):
    parent, path = os.path.split(path)
    files = _getFileList(origin, path=parent, recursive=recursive, level=1)

    for f in files:
        if f["name"] == path:
            return f
    else:
        return None


@time_this(
    logtarget=__name__ + ".timings",
    message="{func}({func_args},{func_kwargs}) took {timing:.2f}ms",
    incl_func_args=True,
)
def _getFileList(
    origin, path=None, filter=None, recursive=False, level=0, allow_from_cache=True
):
    if origin == FileDestinations.SDCARD:
        sdFileList = printer.get_sd_files()

        files = []
        if sdFileList is not None:
            for f in sdFileList:
                type_path = octoprint.filemanager.get_file_type(f["name"])
                if not type_path:
                    # only supported extensions
                    continue
                else:
                    file_type = type_path[0]

                file = {
                    "type": file_type,
                    "typePath": type_path,
                    "name": f["name"],
                    "display": f["display"] if f["display"] else f["name"],
                    "path": f["name"],
                    "origin": FileDestinations.SDCARD,
                    "refs": {
                        "resource": url_for(
                            ".readGcodeFile",
                            target=FileDestinations.SDCARD,
                            filename=f["name"],
                            _external=True,
                        )
                    },
                }
                if f["size"] is not None:
                    file.update({"size": f["size"]})
                files.append(file)
    else:
        filter_func = None
        if filter:
            filter_func = lambda entry, entry_data: octoprint.filemanager.valid_file_type(
                entry, type=filter
            )

        with _file_cache_mutex:
            cache_key = "{}:{}:{}:{}".format(origin, path, recursive, filter)
            files, lastmodified = _file_cache.get(cache_key, ([], None))
            # recursive needs to be True for lastmodified queries so we get lastmodified of whole subtree - #3422
            if (
                not allow_from_cache
                or lastmodified is None
                or lastmodified
                < fileManager.last_modified(origin, path=path, recursive=True)
            ):
                files = list(
                    fileManager.list_files(
                        origin,
                        path=path,
                        filter=filter_func,
                        recursive=recursive,
                        level=level,
                        force_refresh=not allow_from_cache,
                    )[origin].values()
                )
                lastmodified = fileManager.last_modified(
                    origin, path=path, recursive=True
                )
                _file_cache[cache_key] = (files, lastmodified)

        def analyse_recursively(files, path=None):
            if path is None:
                path = ""

            result = []
            for file_or_folder in files:
                # make a shallow copy in order to not accidentally modify the cached data
                file_or_folder = dict(file_or_folder)

                file_or_folder["origin"] = FileDestinations.LOCAL

                if file_or_folder["type"] == "folder":
                    if "children" in file_or_folder:
                        file_or_folder["children"] = analyse_recursively(
                            file_or_folder["children"].values(),
                            path + file_or_folder["name"] + "/",
                        )

                    file_or_folder["refs"] = {
                        "resource": url_for(
                            ".readGcodeFile",
                            target=FileDestinations.LOCAL,
                            filename=path + file_or_folder["name"],
                            _external=True,
                        )
                    }
                else:
                    if (
                        "analysis" in file_or_folder
                        and octoprint.filemanager.valid_file_type(
                            file_or_folder["name"], type="gcode"
                        )
                    ):
                        file_or_folder["gcodeAnalysis"] = file_or_folder["analysis"]
                        del file_or_folder["analysis"]

                    if (
                        "history" in file_or_folder
                        and octoprint.filemanager.valid_file_type(
                            file_or_folder["name"], type="gcode"
                        )
                    ):
                        # convert print log
                        history = file_or_folder["history"]
                        del file_or_folder["history"]
                        success = 0
                        failure = 0
                        last = None
                        for entry in history:
                            success += 1 if "success" in entry and entry["success"] else 0
                            failure += (
                                1 if "success" in entry and not entry["success"] else 0
                            )
                            if not last or (
                                "timestamp" in entry
                                and "timestamp" in last
                                and entry["timestamp"] > last["timestamp"]
                            ):
                                last = entry
                        if last:
                            prints = {
                                "success": success,
                                "failure": failure,
                                "last": {
                                    "success": last["success"],
                                    "date": last["timestamp"],
                                },
                            }
                            if "printTime" in last:
                                prints["last"]["printTime"] = last["printTime"]
                            file_or_folder["prints"] = prints

                    file_or_folder["refs"] = {
                        "resource": url_for(
                            ".readGcodeFile",
                            target=FileDestinations.LOCAL,
                            filename=file_or_folder["path"],
                            _external=True,
                        ),
                        "download": url_for("index", _external=True)
                        + "downloads/files/"
                        + FileDestinations.LOCAL
                        + "/"
                        + file_or_folder["path"],
                    }

                result.append(file_or_folder)

            return result

        files = analyse_recursively(files)

    return files


def _verifyFileExists(origin, filename):
    if origin == FileDestinations.SDCARD:
        return filename in (x["name"] for x in printer.get_sd_files())
    else:
        return fileManager.file_exists(origin, filename)


def _verifyFolderExists(origin, foldername):
    if origin == FileDestinations.SDCARD:
        return False
    else:
        return fileManager.folder_exists(origin, foldername)


def _isBusy(target, path):
    currentOrigin, currentPath = _getCurrentFile()
    if (
        currentPath is not None
        and currentOrigin == target
        and fileManager.file_in_path(FileDestinations.LOCAL, path, currentPath)
        and (printer.is_printing() or printer.is_paused())
    ):
        return True

    return any(
        target == x[0] and fileManager.file_in_path(FileDestinations.LOCAL, path, x[1])
        for x in fileManager.get_busy_files()
    )


@api.route("/files/<string:target>", methods=["POST"])
@no_firstrun_access
@Permissions.FILES_UPLOAD.require(403)
def uploadGcodeFile(target):
    input_name = "file"
    input_upload_name = (
        input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
    )
    input_upload_path = (
        input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
    )
    if input_upload_name in request.values and input_upload_path in request.values:
        if target not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
            return make_response("Unknown target: %s" % target, 404)

        upload = octoprint.filemanager.util.DiskFileWrapper(
            request.values[input_upload_name], request.values[input_upload_path]
        )

        # Store any additional user data the caller may have passed.
        userdata = None
        if "userdata" in request.values:
            import json

            try:
                userdata = json.loads(request.values["userdata"])
            except Exception:
                return make_response("userdata contains invalid JSON", 400)

        if target == FileDestinations.SDCARD and not settings().getBoolean(
            ["feature", "sdSupport"]
        ):
            return make_response("SD card support is disabled", 404)

        sd = target == FileDestinations.SDCARD
        selectAfterUpload = (
            "select" in request.values
            and request.values["select"] in valid_boolean_trues
            and Permissions.FILES_SELECT.can()
        )
        printAfterSelect = (
            "print" in request.values
            and request.values["print"] in valid_boolean_trues
            and Permissions.PRINT.can()
        )

        if sd:
            # validate that all preconditions for SD upload are met before attempting it
            if not (
                printer.is_operational()
                and not (printer.is_printing() or printer.is_paused())
            ):
                return make_response(
                    "Can not upload to SD card, printer is either not operational or already busy",
                    409,
                )
            if not printer.is_sd_ready():
                return make_response(
                    "Can not upload to SD card, not yet initialized", 409
                )

        # determine future filename of file to be uploaded, abort if it can't be uploaded
        try:
            # FileDestinations.LOCAL = should normally be target, but can't because SDCard handling isn't implemented yet
            canonPath, canonFilename = fileManager.canonicalize(
                FileDestinations.LOCAL, upload.filename
            )
            futurePath = fileManager.sanitize_path(FileDestinations.LOCAL, canonPath)
            futureFilename = fileManager.sanitize_name(
                FileDestinations.LOCAL, canonFilename
            )
        except Exception:
            canonFilename = None
            futurePath = None
            futureFilename = None

        if futureFilename is None:
            return make_response(
                "Can not upload file %s, wrong format?" % upload.filename, 415
            )

        if "path" in request.values and request.values["path"]:
            # we currently only support uploads to sdcard via local, so first target is local instead of "target"
            futurePath = fileManager.sanitize_path(
                FileDestinations.LOCAL, request.values["path"]
            )

        # prohibit overwriting currently selected file while it's being printed
        futureFullPath = fileManager.join_path(
            FileDestinations.LOCAL, futurePath, futureFilename
        )
        futureFullPathInStorage = fileManager.path_in_storage(
            FileDestinations.LOCAL, futureFullPath
        )

        if not printer.can_modify_file(futureFullPathInStorage, sd):
            return make_response(
                "Trying to overwrite file that is currently being printed: %s"
                % futureFullPath,
                409,
            )

        reselect = printer.is_current_file(futureFullPathInStorage, sd)

        user = current_user.get_name()

        def fileProcessingFinished(filename, absFilename, destination):
            """
            Callback for when the file processing (upload, optional slicing, addition to analysis queue) has
            finished.

            Depending on the file's destination triggers either streaming to SD card or directly calls selectAndOrPrint.
            """

            if (
                destination == FileDestinations.SDCARD
                and octoprint.filemanager.valid_file_type(filename, "machinecode")
            ):
                return filename, printer.add_sd_file(
                    filename,
                    absFilename,
                    on_success=selectAndOrPrint,
                    tags={"source:api", "api:files.sd"},
                )
            else:
                selectAndOrPrint(filename, absFilename, destination)
                return filename

        def selectAndOrPrint(filename, absFilename, destination):
            """
            Callback for when the file is ready to be selected and optionally printed. For SD file uploads this is only
            the case after they have finished streaming to the printer, which is why this callback is also used
            for the corresponding call to addSdFile.

            Selects the just uploaded file if either selectAfterUpload or printAfterSelect are True, or if the
            exact file is already selected, such reloading it.
            """
            if octoprint.filemanager.valid_file_type(added_file, "gcode") and (
                selectAfterUpload or printAfterSelect or reselect
            ):
                printer.select_file(
                    absFilename,
                    destination == FileDestinations.SDCARD,
                    printAfterSelect,
                    user,
                )

        try:
            added_file = fileManager.add_file(
                FileDestinations.LOCAL,
                futureFullPathInStorage,
                upload,
                allow_overwrite=True,
                display=canonFilename,
            )
        except octoprint.filemanager.storage.StorageError as e:
            if e.code == octoprint.filemanager.storage.StorageError.INVALID_FILE:
                return make_response(
                    'Could not upload the file "{}", invalid type'.format(
                        upload.filename
                    ),
                    400,
                )
            else:
                return make_response(
                    'Could not upload the file "{}"'.format(upload.filename), 500
                )

        if octoprint.filemanager.valid_file_type(added_file, "stl"):
            filename = added_file
            done = True
        else:
            filename = fileProcessingFinished(
                added_file,
                fileManager.path_on_disk(FileDestinations.LOCAL, added_file),
                target,
            )
            done = not sd

        if userdata is not None:
            # upload included userdata, add this now to the metadata
            fileManager.set_additional_metadata(
                FileDestinations.LOCAL, added_file, "userdata", userdata
            )

        sdFilename = None
        if isinstance(filename, tuple):
            filename, sdFilename = filename

        payload = {
            "name": futureFilename,
            "path": filename,
            "target": target,
            "select": selectAfterUpload,
            "print": printAfterSelect,
        }
        if userdata is not None:
            payload["userdata"] = userdata
        eventManager.fire(Events.UPLOAD, payload)

        files = {}
        location = url_for(
            ".readGcodeFile",
            target=FileDestinations.LOCAL,
            filename=filename,
            _external=True,
        )
        files.update(
            {
                FileDestinations.LOCAL: {
                    "name": futureFilename,
                    "path": filename,
                    "origin": FileDestinations.LOCAL,
                    "refs": {
                        "resource": location,
                        "download": url_for("index", _external=True)
                        + "downloads/files/"
                        + FileDestinations.LOCAL
                        + "/"
                        + filename,
                    },
                }
            }
        )

        if sd and sdFilename:
            location = url_for(
                ".readGcodeFile",
                target=FileDestinations.SDCARD,
                filename=sdFilename,
                _external=True,
            )
            files.update(
                {
                    FileDestinations.SDCARD: {
                        "name": sdFilename,
                        "path": sdFilename,
                        "origin": FileDestinations.SDCARD,
                        "refs": {"resource": location},
                    }
                }
            )

        r = make_response(jsonify(files=files, done=done), 201)
        r.headers["Location"] = location
        return r

    elif "foldername" in request.values:
        foldername = request.values["foldername"]

        if target not in [FileDestinations.LOCAL]:
            return make_response("Unknown target: %s" % target, 400)

        canonPath, canonName = fileManager.canonicalize(target, foldername)
        futurePath = fileManager.sanitize_path(target, canonPath)
        futureName = fileManager.sanitize_name(target, canonName)
        if not futureName or not futurePath:
            return make_response("Can't create a folder with an empty name", 400)

        if "path" in request.values and request.values["path"]:
            futurePath = fileManager.sanitize_path(
                FileDestinations.LOCAL, request.values["path"]
            )

        futureFullPath = fileManager.join_path(target, futurePath, futureName)
        if octoprint.filemanager.valid_file_type(futureName):
            return make_response(
                "Can't create a folder named %s, please try another name" % futureName,
                409,
            )

        try:
            added_folder = fileManager.add_folder(
                target, futureFullPath, display=canonName
            )
        except octoprint.filemanager.storage.StorageError as e:
            if e.code == octoprint.filemanager.storage.StorageError.INVALID_DIRECTORY:
                return make_response(
                    "Could not create folder {}, invalid directory".format(futureName)
                )
            else:
                return make_response("Could not create folder {}".format(futureName))

        location = url_for(
            ".readGcodeFile",
            target=FileDestinations.LOCAL,
            filename=added_folder,
            _external=True,
        )
        folder = {
            "name": futureName,
            "path": added_folder,
            "origin": target,
            "refs": {"resource": location},
        }

        r = make_response(jsonify(folder=folder, done=True), 201)
        r.headers["Location"] = location
        return r

    else:
        return make_response("No file to upload and no folder to create", 400)


@api.route("/files/<string:target>/<path:filename>", methods=["POST"])
@no_firstrun_access
def gcodeFileCommand(filename, target):
    if target not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
        return make_response("Unknown target: %s" % target, 404)

    # valid file commands, dict mapping command name to mandatory parameters
    valid_commands = {
        "select": [],
        "slice": [],
        "analyse": [],
        "copy": ["destination"],
        "move": ["destination"],
        "id": [],
    }

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    user = current_user.get_name()

    if command == "select":
        with Permissions.FILES_SELECT.require(403):
            if not _verifyFileExists(target, filename):
                return make_response(
                    "File not found on '%s': %s" % (target, filename), 404
                )

            # selects/loads a file
            if not octoprint.filemanager.valid_file_type(filename, type="machinecode"):
                return make_response(
                    "Cannot select {filename} for printing, not a machinecode file".format(
                        **locals()
                    ),
                    415,
                )

            if not printer.is_ready():
                return make_response(
                    "Printer is already printing, cannot select a new file", 409
                )

            printAfterLoading = False
            if "print" in data and data["print"] in valid_boolean_trues:
                with Permissions.PRINT.require(403):
                    if not printer.is_operational():
                        return make_response(
                            "Printer is not operational, cannot directly start printing",
                            409,
                        )
                    printAfterLoading = True

            sd = False
            if target == FileDestinations.SDCARD:
                filenameToSelect = filename
                sd = True
            else:
                filenameToSelect = fileManager.path_on_disk(target, filename)
            printer.select_file(filenameToSelect, sd, printAfterLoading, user)

    elif command == "slice":
        with Permissions.SLICE.require(403):
            if not _verifyFileExists(target, filename):
                return make_response(
                    "File not found on '%s': %s" % (target, filename), 404
                )

            try:
                if "slicer" in data:
                    slicer = data["slicer"]
                    del data["slicer"]
                    slicer_instance = slicingManager.get_slicer(slicer)

                elif "cura" in slicingManager.registered_slicers:
                    slicer = "cura"
                    slicer_instance = slicingManager.get_slicer("cura")

                else:
                    return make_response(
                        "Cannot slice {filename}, no slicer available".format(**locals()),
                        415,
                    )
            except octoprint.slicing.UnknownSlicer as e:
                return make_response(
                    "Slicer {slicer} is not available".format(slicer=e.slicer), 400
                )

            if not any(
                [
                    octoprint.filemanager.valid_file_type(filename, type=source_file_type)
                    for source_file_type in slicer_instance.get_slicer_properties().get(
                        "source_file_types", ["model"]
                    )
                ]
            ):
                return make_response(
                    "Cannot slice {filename}, not a model file".format(**locals()), 415
                )

            cores = psutil.cpu_count()
            if (
                slicer_instance.get_slicer_properties().get("same_device", True)
                and (printer.is_printing() or printer.is_paused())
                and (cores is None or cores < 2)
            ):
                # slicer runs on same device as OctoPrint, slicing while printing is hence disabled
                return make_response(
                    "Cannot slice on {slicer} while printing on single core systems or systems of unknown core count due to performance reasons".format(
                        **locals()
                    ),
                    409,
                )

            if "destination" in data and data["destination"]:
                destination = data["destination"]
                del data["destination"]
            elif "gcode" in data and data["gcode"]:
                destination = data["gcode"]
                del data["gcode"]
            else:
                import os

                name, _ = os.path.splitext(filename)
                destination = (
                    name
                    + "."
                    + slicer_instance.get_slicer_properties().get(
                        "destination_extensions", ["gco", "gcode", "g"]
                    )[0]
                )

            full_path = destination
            if "path" in data and data["path"]:
                full_path = fileManager.join_path(target, data["path"], destination)
            else:
                path, _ = fileManager.split_path(target, filename)
                if path:
                    full_path = fileManager.join_path(target, path, destination)

            canon_path, canon_name = fileManager.canonicalize(target, full_path)
            sanitized_name = fileManager.sanitize_name(target, canon_name)

            if canon_path:
                full_path = fileManager.join_path(target, canon_path, sanitized_name)
            else:
                full_path = sanitized_name

            # prohibit overwriting the file that is currently being printed
            currentOrigin, currentFilename = _getCurrentFile()
            if (
                currentFilename == full_path
                and currentOrigin == target
                and (printer.is_printing() or printer.is_paused())
            ):
                make_response(
                    "Trying to slice into file that is currently being printed: %s"
                    % full_path,
                    409,
                )

            if "profile" in data and data["profile"]:
                profile = data["profile"]
                del data["profile"]
            else:
                profile = None

            if "printerProfile" in data and data["printerProfile"]:
                printerProfile = data["printerProfile"]
                del data["printerProfile"]
            else:
                printerProfile = None

            if (
                "position" in data
                and data["position"]
                and isinstance(data["position"], dict)
                and "x" in data["position"]
                and "y" in data["position"]
            ):
                position = data["position"]
                del data["position"]
            else:
                position = None

            select_after_slicing = False
            if "select" in data and data["select"] in valid_boolean_trues:
                if not printer.is_operational():
                    return make_response(
                        "Printer is not operational, cannot directly select for printing",
                        409,
                    )
                select_after_slicing = True

            print_after_slicing = False
            if "print" in data and data["print"] in valid_boolean_trues:
                if not printer.is_operational():
                    return make_response(
                        "Printer is not operational, cannot directly start printing", 409
                    )
                select_after_slicing = print_after_slicing = True

            override_keys = [
                k for k in data if k.startswith("profile.") and data[k] is not None
            ]
            overrides = {}
            for key in override_keys:
                overrides[key[len("profile.") :]] = data[key]

            def slicing_done(target, path, select_after_slicing, print_after_slicing):
                if select_after_slicing or print_after_slicing:
                    sd = False
                    if target == FileDestinations.SDCARD:
                        filenameToSelect = path
                        sd = True
                    else:
                        filenameToSelect = fileManager.path_on_disk(target, path)
                    printer.select_file(filenameToSelect, sd, print_after_slicing, user)

            try:
                fileManager.slice(
                    slicer,
                    target,
                    filename,
                    target,
                    full_path,
                    profile=profile,
                    printer_profile_id=printerProfile,
                    position=position,
                    overrides=overrides,
                    display=canon_name,
                    callback=slicing_done,
                    callback_args=(
                        target,
                        full_path,
                        select_after_slicing,
                        print_after_slicing,
                    ),
                )
            except octoprint.slicing.UnknownProfile:
                return make_response(
                    "Profile {profile} doesn't exist".format(**locals()), 400
                )

            files = {}
            location = url_for(
                ".readGcodeFile", target=target, filename=full_path, _external=True
            )
            result = {
                "name": destination,
                "path": full_path,
                "display": canon_name,
                "origin": FileDestinations.LOCAL,
                "refs": {
                    "resource": location,
                    "download": url_for("index", _external=True)
                    + "downloads/files/"
                    + target
                    + "/"
                    + full_path,
                },
            }

            r = make_response(jsonify(result), 202)
            r.headers["Location"] = location
            return r

    elif command == "analyse":
        with Permissions.FILES_UPLOAD.require(403):
            if not _verifyFileExists(target, filename):
                return make_response(
                    "File not found on '%s': %s" % (target, filename), 404
                )

            printer_profile = None
            if "printerProfile" in data and data["printerProfile"]:
                printer_profile = data["printerProfile"]

            if not fileManager.analyse(
                target, filename, printer_profile_id=printer_profile
            ):
                return make_response(
                    "No analysis possible for {} on {}".format(filename, target), 400
                )

    elif command == "copy" or command == "move":
        with Permissions.FILES_UPLOAD.require(403):
            # Copy and move are only possible on local storage
            if target not in [FileDestinations.LOCAL]:
                return make_response(
                    "Unsupported target for {}: {}".format(command, target), 400
                )

            if not _verifyFileExists(target, filename) and not _verifyFolderExists(
                target, filename
            ):
                return make_response(
                    "File or folder not found on {}: {}".format(target, filename), 404
                )

            path, name = fileManager.split_path(target, filename)

            destination = data["destination"]
            dst_path, dst_name = fileManager.split_path(target, destination)
            sanitized_destination = fileManager.join_path(
                target, dst_path, fileManager.sanitize_name(target, dst_name)
            )

            if (
                _verifyFolderExists(target, destination)
                and sanitized_destination != filename
            ):
                # destination is an existing folder and not ourselves (= display rename), we'll assume we are supposed
                # to move filename to this folder under the same name
                destination = fileManager.join_path(target, destination, name)

            if _verifyFileExists(target, destination) or _verifyFolderExists(
                target, destination
            ):
                return make_response(
                    "File or folder does already exist on {}: {}".format(
                        target, destination
                    ),
                    409,
                )

            is_file = fileManager.file_exists(target, filename)
            is_folder = fileManager.folder_exists(target, filename)

            if not (is_file or is_folder):
                return make_response(
                    "{} on {} is neither file or folder, can't {}".format(
                        filename, target, command
                    ),
                    400,
                )

            if command == "copy":
                # destination already there? error...
                if _verifyFileExists(target, destination) or _verifyFolderExists(
                    target, destination
                ):
                    return make_response(
                        "File or folder does already exist on {}: {}".format(
                            target, destination
                        ),
                        409,
                    )

                if is_file:
                    fileManager.copy_file(target, filename, destination)
                else:
                    fileManager.copy_folder(target, filename, destination)

            elif command == "move":
                with Permissions.FILES_DELETE.require(403):
                    if _isBusy(target, filename):
                        return make_response(
                            "Trying to move a file or folder that is currently in use: {}".format(
                                filename
                            ),
                            409,
                        )

                    # destination already there AND not ourselves (= display rename)? error...
                    if (
                        _verifyFileExists(target, destination)
                        or _verifyFolderExists(target, destination)
                    ) and sanitized_destination != filename:
                        return make_response(
                            "File or folder does already exist on {}: {}".format(
                                target, destination
                            ),
                            409,
                        )

                    # deselect the file if it's currently selected
                    currentOrigin, currentFilename = _getCurrentFile()
                    if currentFilename is not None and filename == currentFilename:
                        printer.unselect_file()

                    if is_file:
                        fileManager.move_file(target, filename, destination)
                    else:
                        fileManager.move_folder(target, filename, destination)

            location = url_for(
                ".readGcodeFile", target=target, filename=destination, _external=True
            )
            result = {
                "name": name,
                "path": destination,
                "origin": FileDestinations.LOCAL,
                "refs": {"resource": location},
            }
            if is_file:
                result["refs"]["download"] = (
                    url_for("index", _external=True)
                    + "downloads/files/"
                    + target
                    + "/"
                    + destination
                )

            r = make_response(jsonify(result), 201)
            r.headers["Location"] = location
            return r

    elif command == "id":
        if "trans_id" in data:
            trans_id = data["trans_id"]
            del data["trans_id"]
            fileManager.remove_additional_metadata(target, filename, "trans_id")
            fileManager.set_additional_metadata(target, filename, "trans_id", trans_id)

    return NO_CONTENT


@api.route("/files/<string:target>/<path:filename>", methods=["DELETE"])
@no_firstrun_access
@Permissions.FILES_DELETE.require(403)
def deleteGcodeFile(filename, target):
    if not _verifyFileExists(target, filename) and not _verifyFolderExists(
        target, filename
    ):
        return make_response(
            "File/Folder not found on '%s': %s" % (target, filename), 404
        )

    if _verifyFileExists(target, filename):
        if target not in [FileDestinations.LOCAL, FileDestinations.SDCARD]:
            return make_response("Unknown target: %s" % target, 400)

        if _isBusy(target, filename):
            return make_response(
                "Trying to delete a file that is currently in use: %s" % filename, 409
            )

        # deselect the file if it's currently selected
        currentOrigin, currentPath = _getCurrentFile()
        if (
            currentPath is not None
            and currentOrigin == target
            and filename == currentPath
        ):
            printer.unselect_file()

        # delete it
        if target == FileDestinations.SDCARD:
            printer.delete_sd_file(filename, tags={"source:api", "api:files.sd"})
        else:
            fileManager.remove_file(target, filename)

    elif _verifyFolderExists(target, filename):
        if target not in [FileDestinations.LOCAL]:
            return make_response("Unknown target: %s" % target, 400)

        if _isBusy(target, filename):
            return make_response(
                "Trying to delete a folder that contains a file that is currently in use: %s"
                % filename,
                409,
            )

        # deselect the file if it's currently selected
        currentOrigin, currentPath = _getCurrentFile()
        if (
            currentPath is not None
            and currentOrigin == target
            and fileManager.file_in_path(target, filename, currentPath)
        ):
            printer.unselect_file()

        # delete it
        fileManager.remove_folder(target, filename, recursive=True)

    return NO_CONTENT


def _getCurrentFile():
    currentJob = printer.get_current_job()
    if (
        currentJob is not None
        and "file" in currentJob
        and "path" in currentJob["file"]
        and "origin" in currentJob["file"]
    ):
        return currentJob["file"]["origin"], currentJob["file"]["path"]
    else:
        return None, None


class WerkzeugFileWrapper(octoprint.filemanager.util.AbstractFileWrapper):
    """
    A wrapper around a Werkzeug ``FileStorage`` object.

    Arguments:
        file_obj (werkzeug.datastructures.FileStorage): The Werkzeug ``FileStorage`` instance to wrap.

    .. seealso::

       `werkzeug.datastructures.FileStorage <http://werkzeug.pocoo.org/docs/0.10/datastructures/#werkzeug.datastructures.FileStorage>`_
            The documentation of Werkzeug's ``FileStorage`` class.
    """

    def __init__(self, file_obj):
        octoprint.filemanager.util.AbstractFileWrapper.__init__(self, file_obj.filename)
        self.file_obj = file_obj

    def save(self, path):
        """
        Delegates to ``werkzeug.datastructures.FileStorage.save``
        """
        self.file_obj.save(path)

    def stream(self):
        """
        Returns ``werkzeug.datastructures.FileStorage.stream``
        """
        return self.file_obj.stream
