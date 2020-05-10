
from ..renderer.base import RenderContext
from ..renderer import format_parser_error, DoxygenToRstRendererFactory
from ..parser import ParserError, FileIOError

from breathe.project import ProjectInfoFactory, ProjectInfo
from breathe.finder.core import FinderFactory, Filter
from breathe.parser import DoxygenParserFactory
from breathe.renderer.filter import FilterFactory
from breathe.renderer.mask import MaskFactoryBase
from breathe.renderer.target import TargetHandler

from sphinx.directives import SphinxDirective

from docutils import nodes
from docutils.nodes import Node

from typing import List


class WarningHandler:
    def __init__(self, state, context):
        self.state = state
        self.context = context

    def warn(self, raw_text, rendered_nodes=None):
        raw_text = self.format(raw_text)
        if rendered_nodes is None:
            rendered_nodes = [nodes.paragraph("", "", nodes.Text(raw_text))]
        return [
            nodes.warning("", *rendered_nodes),
            self.state.document.reporter.warning(raw_text, line=self.context['lineno'])
            ]

    def format(self, text):
        return text.format(**self.context)


def create_warning(project_info, state, lineno, **kwargs):
    tail = ''
    if project_info:
        tail = 'in doxygen xml output for project "{project}" from directory: {path}'.format(
            project=project_info.name(),
            path=project_info.project_path()
            )

    context = dict(
        lineno=lineno,
        tail=tail,
        **kwargs
        )

    return WarningHandler(state, context)


class BaseDirective(SphinxDirective):
    def __init__(self, finder_factory: FinderFactory,
                 project_info_factory: ProjectInfoFactory,
                 parser_factory: DoxygenParserFactory,
                 *args) -> None:
        super().__init__(*args)
        self.directive_args = list(args)  # Convert tuple to list to allow modification.

        self.finder_factory = finder_factory
        self.project_info_factory = project_info_factory
        self.filter_factory = FilterFactory(self.env.app)
        self.parser_factory = parser_factory

    @property
    def kind(self) -> str:
        raise NotImplementedError

    def render(self, node_stack, project_info: ProjectInfo, filter_: Filter,
               target_handler: TargetHandler, mask_factory: MaskFactoryBase,
               directive_args) -> List[Node]:
        "Standard render process used by subclasses"

        renderer_factory = DoxygenToRstRendererFactory(self.parser_factory, project_info)
        try:
            object_renderer = renderer_factory.create_renderer(
                node_stack,
                self.state,
                self.state.document,
                filter_,
                target_handler,
                )
        except ParserError as e:
            return format_parser_error("doxygenclass", e.error, e.filename, self.state,
                                       self.lineno, True)
        except FileIOError as e:
            return format_parser_error("doxygenclass", e.error, e.filename, self.state,
                                       self.lineno, True)

        context = RenderContext(node_stack, mask_factory, directive_args)
        return object_renderer.render(node_stack[0], context)
