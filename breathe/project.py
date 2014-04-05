
from breathe.exception import BreatheError

import os

class ProjectError(BreatheError):
    pass

class NoDefaultProjectError(ProjectError):
    pass

class AutoProjectInfo(object):

    def __init__(
            self,
            name,
            source_path,
            build_dir,
            reference,
            source_dir,
            domain_by_extension,
            domain_by_file_pattern,
            match
            ):

        self._name = name
        self._source_path = source_path
        self._build_dir = build_dir
        self._reference = reference
        self._source_dir = source_dir
        self._domain_by_extension = domain_by_extension
        self._domain_by_file_pattern = domain_by_file_pattern
        self._match = match

    def name(self):
        return self._name

    def build_dir(self):
        return self._build_dir

    def abs_path_to_source_file(self, file_):
        """
        Returns full path to the provide file assuming that the provide path is relative to the
        projects source directory as specified in the breathe_projects_source config variable.
        """

        if os.path.isabs(self._source_path):
            full_source_path = self._source_path
        else:
            full_source_path = os.path.realpath(self._source_path)

        return os.path.join(full_source_path, file_)

    def create_project_info(self, project_path):

        return ProjectInfo(
            self._name,
            project_path,
            self._source_path,
            self._reference,
            self._source_dir,
            self._domain_by_extension,
            self._domain_by_file_pattern,
            self._match
            )

class ProjectInfo(object):

    def __init__(
            self,
            name,
            path,
            source_path,
            reference,
            source_dir,
            domain_by_extension,
            domain_by_file_pattern,
            match
            ):

        self._name = name
        self._project_path = path
        self._source_path = source_path
        self._reference = reference
        self._source_dir = source_dir
        self._domain_by_extension = domain_by_extension
        self._domain_by_file_pattern = domain_by_file_pattern
        self._match = match

    def name(self):
        return self._name

    def project_path(self):
        return self._project_path

    def source_path(self):
        return self._source_path

    def relative_path_to_xml_file(self, file_):
        """
        Returns relative path from Sphinx documentation top-level source directory to the specified
        file assuming that the specified file is a path relative to the doxygen xml output directory.
        """
        if os.path.isabs(self._project_path):
            full_xml_project_path = self._project_path
        else:
            full_xml_project_path = os.path.realpath(self._project_path)

        return os.path.relpath(
                os.path.join(full_xml_project_path, file_),
                self._source_dir
                )

    def sphinx_abs_path_to_file(self, file_):
        """
        Prepends os.path.sep to the value returned by relative_path_to_file.

        This is to match Sphinx's concept of an absolute path which starts from the top-level source
        directory of the project.
        """
        return os.path.sep + self.relative_path_to_xml_file(file_)

    def reference(self):
        return self._reference

    def domain_for_file(self, file_):

        domain = ""
        extension = file_.split(".")[-1]

        try:
            domain = self._domain_by_extension[extension]
        except KeyError:
            pass

        for pattern, pattern_domain in self._domain_by_file_pattern.items():
            if self._match(file_, pattern):
                domain = pattern_domain

        return domain


class ProjectInfoFactory(object):

    def __init__(self, source_dir, build_dir, match):

        self.source_dir = source_dir
        self.build_dir = build_dir
        self.match = match

        self.projects = {}
        self.default_project = None
        self.domain_by_extension = {}
        self.domain_by_file_pattern = {}

        self.project_count = 0
        self.project_info_store = {}
        self.auto_project_info_store = {}

    def update(
            self,
            projects,
            default_project,
            domain_by_extension,
            domain_by_file_pattern,
            projects_source,
            build_dir
            ):

        self.projects = projects
        self.default_project = default_project
        self.domain_by_extension = domain_by_extension
        self.domain_by_file_pattern = domain_by_file_pattern
        self.projects_source = projects_source

        # If the breathe config values has a non-empty value for build_dir then use that otherwise
        # stick with the default
        if build_dir:
            self.build_dir = build_dir

    def default_path(self):

        if not self.default_project:
            raise NoDefaultProjectError(
                    "No breathe_default_project config setting to fall back on "
                    "for directive with no 'project' or 'path' specified."
                    )

        try:
            return self.projects[self.default_project]
        except KeyError:
            raise ProjectError(
                    ( "breathe_default_project value '%s' does not seem to be a valid key for the "
                      "breathe_projects dictionary" ) % self.default_project
                    )

    def create_project_info(self, options):

        name = ""

        if "project" in options:
            try:
                path = self.projects[options["project"]]
                name = options["project"]
            except KeyError:
                raise ProjectError( "Unable to find project '%s' in breathe_projects dictionary" % options["project"] )

        elif "path" in options:
            path = options["path"]

        else:
            path = self.default_path()

        try:
            return self.project_info_store[path]
        except KeyError:

            reference = name

            if not name:
                name = "project%s" % self.project_count
                reference = path
                self.project_count += 1

            project_info = ProjectInfo(
                    name,
                    path,
                    "NoSourcePath",
                    reference,
                    self.source_dir,
                    self.domain_by_extension,
                    self.domain_by_file_pattern,
                    self.match
                    )

            self.project_info_store[path] = project_info

            return project_info

    def create_auto_project_info(self, options):

        name = ""

        if "source" in options:
            try:
                source_path = self.projects_source[options["source"]]
                name = options["source"]
            except KeyError:
                raise ProjectError( "Unable to find project '%s' in breathe_projects_source dictionary" % options["source"] )

        elif "source-path" in options:
            source_path = options["source-path"]

        else:
            raise ProjectError( "Unable to find either :project: or :path: specified" )

        # Key off the name concenated with the source path so that users can force separate projects
        # by specifying different source names for different directives even if they have the same
        # source path. This allows the autodoxygenindex directive to be used to represent specific
        # parts of a project by providing the relevant files and then declaring a source name which
        # is different to other autodoxygenindex directives which might be using the same
        # source_path.
        key = source_path
        if name:
            key = "%s:%s" % (name, source_path)

        try:
            return self.auto_project_info_store[key]
        except KeyError:

            reference = name

            if not name:
                name = "project%s" % self.project_count
                reference = source_path
                self.project_count += 1

            auto_project_info = AutoProjectInfo(
                    name,
                    source_path,
                    self.build_dir,
                    reference,
                    self.source_dir,
                    self.domain_by_extension,
                    self.domain_by_file_pattern,
                    self.match
                    )

            self.auto_project_info_store[key] = auto_project_info

            return auto_project_info

