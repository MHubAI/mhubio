import os
import setuptools

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# install locally via `pip install -e .` (-> for development)
# install from github via `pip install git+https://github.com/MHubAI/mhubio (-> in Dockerfiles)

setuptools.setup(
    name = "mhubio",
    version = "0.0.1",
    author = "Leonard Nürnberg",
    author_email = "lnuernberg@bwh.harvard.edu",
    description = ("The glue layer framework used to harmonize MHub model's input and output data."),
    license = "MIT",
    keywords = "mhub",
    url = "https://github.com/MHubAI/mhubio",
    packages=setuptools.find_packages(),
    long_description=read('README.md'),
    package_data={'': ['utils/ymldicomseg/data/*.csv']},
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
    ],
)
