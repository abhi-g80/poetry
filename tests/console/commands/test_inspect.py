from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency_group import DependencyGroup

from poetry.factory import Factory
from tests.helpers import TestLocker
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.types import CommandTesterFactory


TEST_DATA = {
    "metadata_version": 2.1,
    "name": "test-package-1",
    "version": "1.2.3",
    "summary": "this is a test package",
    "author_email": "testauthor@email.com",
    "author": "testauthor",
}


class MockedDistribution:
    def __init__(self, json: dict):
        self.json = json

    @property
    def entry_points(self):
        return self.json.get("entry_points", [])

    @property
    def metadata(self):
        return type("Object", (), {"json": self.json})()


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("inspect")


def test_inspect_basic_with_installed_packages(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    tester.execute()

    expected = """\
Could not find package metadata for name: simple-project: showing basic info
Name
 simple-project

Version
 1.2.3

Package description
 Some description.

"""

    assert tester.io.fetch_output() == expected


def _configure_project_with_groups(poetry: Poetry, installed: Repository) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))

    poetry.package.add_dependency_group(DependencyGroup(name="time", optional=True))
    poetry.package.add_dependency(
        Factory.create_dependency("pendulum", "^2.0.0", groups=["time"])
    )

    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "^3.7.3", groups=["test"])
    )

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (
            "",
            """\
Name
 test-package-1

Version
 1.2.3

Package description
 Some description.

Author email
 testauthor@email.com

Author
 testauthor

""",
        ),
        (
            "--json",
            """\
""",
        ),
        (
            "--compact",
            """\
 Name                 : test-package-1
 Version              : 1.2.3
 Package description  : Some description.
 Author email         : testauthor@email.com
 Author               : testauthor
""",
        ),
        (
            "--list-properties",
            """\
Available properties for simple-project are:
- name
- version
- package_description
- metadata_version
- summary
- author_email
- author
""",
        ),
        (
            "--property name",
            """\
Name
 test-package-1

""",
        ),
    ],
)
def test_show_basic_with_group_options(
    options: str,
    expected: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    mocker: MockerFixture,
) -> None:
    _configure_project_with_groups(poetry, installed)
    testinstance = MockedDistribution(TEST_DATA)

    mocker.patch("importlib.metadata.Distribution.from_name", return_value=testinstance)

    tester.execute(options)

    assert tester.io.fetch_output() == expected
