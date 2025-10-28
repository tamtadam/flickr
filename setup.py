from os import path
from setuptools import setup

try:
    execfile
except NameError:

    def execfile(fname, globs, locs=None):
        locs = locs or globs
        exec(compile(open(fname).read(), fname, "exec"), globs, locs)


version_ns = {}
try:
    execfile(path.join(path.abspath(path.dirname(__file__)), "_version.py"), version_ns)
except EnvironmentError:
    version = "dev"
else:
    version = version_ns.get("__version__", "dev")

setup(
    name="flickr",
    description="flickr",
    author="",
    version=version,
    author_email="",
    packages=["flickr"],
    package_data={
        "flickr": ["**/**", "**/**/**", "**/**/**/**", "**/**/**/**/**", "**/**/**/**/**/**"],
    },
    include_package_data=True,
)
