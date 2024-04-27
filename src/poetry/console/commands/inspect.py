from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.option import Option
from packaging.utils import canonicalize_name

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from importlib.metadata import Distribution

    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option
    from cleo.ui.table import Rows
    from poetry.core.packages.package import Package

# Define the gap required after new-line for displaying items in list in when in --compact
DISPLAY_GAP_FOR_SAME_KEY = "\n   "

MAX_DISPLAY_LINE_LENGTH = 79

# Metadata properties which are not needed, redundant or may not provide best visualization
# when display with other properties.
SKIP_PROPERTIES = ("description", "summary", "metadata_version")

# Metadata properties which may hold URL(s)
URL_PROPERTIES = ("project_url",)

# Metadata properties which may be longer than MAX_DISPLAY_LINE_LENGTH
LONG_PROPERTIES = ("license",)


def display_pretty_urls(urls: list[str]) -> str:
    res = []
    for url in urls:
        name, url_ = url.split(",")
        res.append(f"<c1>{name}</> -{url_}")
    return DISPLAY_GAP_FOR_SAME_KEY.join(res)


def display_pretty_list(items: list[str]) -> str:
    return DISPLAY_GAP_FOR_SAME_KEY.join(items)


def prettify(s: str) -> str:
    return s.replace("_", " ").capitalize()


class InspectCommand(Command):
    name = "inspect"
    description = "Inspect metadata."

    arguments: ClassVar[list[Argument]] = [
        argument(
            "dependency",
            "The dependency to inspect. <comment>(inspects root package as default)</comment>",
            optional=True,
        )
    ]
    options: ClassVar[list[Option]] = [
        option("json", "j", "Display metadata as json.", flag=True),
        option("compact", "c", "Display metadata as compact table.", flag=True),
        option(
            "list-properties",
            "l",
            "List all properties available in metadata.",
            flag=True,
        ),
        option(
            "property",
            "p",
            "Show only this property as available in metadata.",
            flag=False,
            multiple=True,
        ),
    ]

    help = (
        """The command shows various information about dependencies and root package."""
    )

    colors: ClassVar[list[str]] = ["cyan", "yellow", "green", "magenta", "blue"]

    def handle(self) -> int:
        dependency = self.argument("dependency")

        pkg = self._get_package_from_dependency(dependency)
        metadata = self.inspect_metadata(pkg)
        available_properties = metadata.keys()

        if self.option("list-properties"):
            props = "\n".join(["- " + x for x in available_properties])
            self.line(f"<b>Available properties for <info>{pkg.name}</info> are:</b>")
            self.line(f"<info>{props}</info>")
            return 0

        props = self.option("property")
        display_metadata = {}
        for prop in props:
            if prop not in available_properties:
                self.line_error(f"<error>Property '{prop}' not available.</error>")
                return 1
            display_metadata[prop] = metadata[prop]

        display_metadata = display_metadata or metadata

        if self.option("json"):
            import json
            import sys

            json.dump(display_metadata, fp=sys.stderr)
        elif self.option("compact"):
            rows = self.build_rows_from_metadata(display_metadata)
            self.table(rows=rows, style="compact").render()
        else:
            self.display_normal(display_metadata, props)

        return 0

    def inspect_metadata(self, package: Package) -> dict[str, str | list[str]]:
        from importlib.metadata import Distribution
        from importlib.metadata import PackageNotFoundError

        metadata: dict[str, str | list[str]] = {
            "name": package.pretty_name,
            "version": package.pretty_version,
            "package_description": package.description,
        }

        try:
            d: Distribution = Distribution.from_name(package.name)
        except PackageNotFoundError:
            self.line(
                f"<warning>Could not find package metadata for name: {package.name}: showing basic info</>"
            )
            return metadata

        # try to get metadata from Distribution.metadata.json
        if hasattr(d.metadata, "json"):
            metadata.update(d.metadata.json)
        else:
            # AttributeError
            self.line(f"<error>Could not find distribution metadata: {package.name}</>")

        # entry points
        if ep := self.get_entry_points(d):
            metadata["entry_points"] = ep

        return metadata

    def get_entry_points(self, dist: Distribution) -> list[str]:
        rows: list[str] = []
        for ep in dist.entry_points:
            rows.append(f"{ep.name} source: {ep.value}")
        return rows

    def _get_package_from_dependency(self, dep: str) -> Package:
        locked_repository = self.poetry.locker.locked_repository()
        locked_packages = locked_repository.packages

        pkg: Package = self.poetry.package
        if dep:
            canonicalized_package = canonicalize_name(dep)

            for locked in locked_packages:
                if locked.name == canonicalized_package:
                    pkg = locked
                    break

            if pkg == self.poetry.package:
                raise ValueError(f"Package '{dep}' not found")
        return pkg

    def build_rows_from_metadata(self, data: dict[str, str | list[str]]) -> Rows:
        rows: Rows = []

        for prop, items in data.items():
            if prop in SKIP_PROPERTIES:
                continue
            if prop in URL_PROPERTIES:
                if isinstance(items, list):
                    items = display_pretty_urls(items)
            elif isinstance(items, list):
                items = display_pretty_list(items)
            if prop in LONG_PROPERTIES and len(items) > MAX_DISPLAY_LINE_LENGTH:
                items = (
                    items[:MAX_DISPLAY_LINE_LENGTH]
                    + f"... <comment>(use <info>-p {prop}</info> to see full {prop})</comment>"
                )
            rows.append([f"<info>{prettify(prop)}</>", f" : <b>{items}</>"])

        return rows

    def display_normal(
        self, data: dict[str, str | list[str]], props: str | list[str]
    ) -> None:
        for key, value in data.items():
            if key in SKIP_PROPERTIES and not props:
                continue
            if props and key not in props:
                continue
            self.line(f"<b><info>{prettify(key)}</info></b>")
            if isinstance(value, list):
                # print as list array
                for item in value:
                    self.line(f"<c1> - {item}</c1>")
            else:
                # print as normal
                self.line(f"<c2> {value}</c2>")
            self.line("")
