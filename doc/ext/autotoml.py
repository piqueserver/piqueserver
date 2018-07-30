# Inspired by https://github.com/Jakski/sphinxcontrib-autoyaml/
import os

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from sphinx.errors import ExtensionError
from sphinx.ext.autodoc import AutodocReporter
from sphinx.util import logging
from sphinx.util.nodes import nested_parse_with_titles

logger = logging.getLogger(__name__)


CONFIG = 1
COMMENT = 2
BLANK = 3

class AutoTOMLException(ExtensionError):
    category = "AutoTOML error"


class AutoTOMLDirective(Directive):

    required_arguments = 1

    def run(self):
        self.config = self.state.document.settings.env.config
        self.env = self.state.document.settings.env
        self.record_dependencies = self.state.document.settings.record_dependencies
        location = os.path.normpath(
            os.path.join(
                self.env.srcdir, self.config.autotoml_root + "/" + self.arguments[0]
            )
        )
        self.result = ViewList()
        if os.path.isfile(location):
            logger.debug("[autotoml] parsing file: %s", location)
            self.parse_file(location)
        else:
            raise AutoTOMLException(
                '%s:%s: location "%s" is not a file.'
                % (
                    self.env.doc2path(self.env.docname, None),
                    self.content_offset - 1,
                    location,
                )
            )
        self.record_dependencies.add(location)
        node = nodes.paragraph()
        # parse comment internals as reST
        old_reporter = self.state.memo.reporter
        self.state.memo.reporter = AutodocReporter(
            self.result, self.state.memo.reporter
        )
        nested_parse_with_titles(self.state, self.result, node)
        self.state.memo.reporter = old_reporter
        return [node]

    def parse_file(self, source):
        with open(source, "r") as src:
            lines = src.read().splitlines()

        logger.critical('thing')

        mod_lines = []
        # mod_lines.append('.. highlight:: toml')
        # mod_lines.append('')

        last = COMMENT
        for line in lines:
            if line.startswith('#'):
                if last != COMMENT:
                    mod_lines.append('')
                last = COMMENT

                if line.startswith('#'):
                    line = line.lstrip('#')
                    if line.startswith(' '):
                        line = line[1:]

                mod_lines.append(line)

            elif line.strip():
                if last != CONFIG:
                    mod_lines.append('')
                    mod_lines.append('::')
                    mod_lines.append('')
                    last = CONFIG
                mod_lines.append('    '+line)
            else:
                last = BLANK
                mod_lines.append('')

        with open('/home/samuel/test.toml', 'w') as f:
            f.write('\n'.join(mod_lines))

        for linenum, line in enumerate(mod_lines, start=1):
            self.result.append(line, source, linenum)


def setup(app):
    app.add_directive("autotoml", AutoTOMLDirective)
    app.add_config_value("autotoml_root", "..", "env")
