#!/usr/bin/env python2
"""
Checks pulp's database models for validation exceptions
Usage:
    sudo -u apache python validation_check.py
"""

import json
import os
import sys
from subprocess import call
import time

from bson.json_util import dumps
from mongoengine import ValidationError
import pkg_resources

from pulp.server.db import model as platform_models
from pulp.server import config
from pulp.server.db import connection as db_connection

VALIDATION_ERROR_MESSAGE = "There were validation errors.  Please see {0} for more information\n"
ERROR_FILE_NAME = "validation_errors_{0}.txt"
MODEL_ENTRY_POINT = 'pulp.unit_models'
MONGOENGINE_MODELS = [platform_models.Repository,
                      platform_models.RepositoryContentUnit,
                      platform_models.Importer,
                      platform_models.ReservedResource,
                      platform_models.Worker,
                      platform_models.MigrationTracker,
                      platform_models.TaskStatus,
                      platform_models.CeleryBeatLock,
                      platform_models.User,
                      platform_models.Distributor]


class ValidationExceptionHandler:
    """
    Handles the output of validation exceptions to the exceptions file.
    """
    def __init__(self, error_file):
        """
        Initializes a ValidationException handler that writes to the specified error_file

        :param error_file: The file to write exceptions to
        :type error_file: file
        """
        self.error_file = error_file

    def _write_newline(self):
        self.error_file.write(os.linesep)

    def handle_exception(self, item, ex):
        """
        Writes the validation error that was thrown to the error file specified in the constructor

        :param item: The object that caused the validation exeption
        :type item: mongoengine.Document

        :param ex: Validation Error thrown by mongoengine
        :type ex: ValidationError
        """
        self.error_file.write("----------------------------------------------")
        self._write_newline()
        self.error_file.write(ex.message)
        self._write_newline()
        self.error_file.write(json.dumps(ex.to_dict()))
        self._write_newline()
        self._write_newline()
        self.error_file.write("Data:")
        self._write_newline()
        self.error_file.write(dumps(item.to_mongo()))
        self._write_newline()


class ValidationCheck:
    """
    Checks if existing database objects will pass new validation requirements.
    """
    def __init__(self, exception_handler):
        """
        :param exception_handler: Handles the processing of a Validation Error
        :type exception_handler: ValidationExceptionHandler
        """
        self.exception_handler = exception_handler
        self.has_exceptions = False
        self._load_plugin_models()

    def check_model(self, model):
        """
        Loops through all objects in the model and attempts to save them back to the
        database, triggering validation logic.

        :param model: The mongoengine model to check
        :type model: mongoengine.Document
        """
        error_count = 0
        for item in model.objects.all():
            try:
                model.save(item)
                sys.stdout.write(".")
            except ValidationError as ex:
                self.has_exceptions = True
                error_count += 1
                self.exception_handler.handle_exception(item, ex)
                sys.stdout.write("E")

            if error_count >= 50:
                sys.stdout.write(os.linesep)
                return

        sys.stdout.write(os.linesep)

    def check(self):
        """
        Loops through all models configured in MONGOENGINE_MODELS and tests them for validity
        """
        for item in MONGOENGINE_MODELS:
            sys.stdout.write(item.__module__ + "." + item.__name__ + ": ")
            self.check_model(item)

    def _load_plugin_models(self):
        for entry_point in pkg_resources.iter_entry_points(MODEL_ENTRY_POINT):
            MONGOENGINE_MODELS.append(entry_point.resolve())

if __name__ == '__main__':
    call(["pulp-manage-db"])

    config.load_configuration()

    db_connection.initialize()

    datetime = time.strftime("%Y%m%d%H%M%S")

    error_file = open(ERROR_FILE_NAME.format(datetime), "w")

    exception_handler = ValidationExceptionHandler(error_file)

    validation = ValidationCheck(exception_handler)
    validation.check()

    if (validation.has_exceptions):
        sys.stdout.write(VALIDATION_ERROR_MESSAGE.format(ERROR_FILE_NAME.format(datetime)))

    error_file.close()
