from importlib.resources import as_file, files

import pytest

from git_ship.model import Profile


@pytest.fixture
def demo():
    with as_file(files("git_ship").joinpath("assets/demo.json")) as path:
        return Profile.read(path)
