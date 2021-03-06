import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pymochad_mqtt",
    version="0.8.9",
    author="Alex Osadchyy",
    author_email="aosadchyy@outlook.com",
    description="Mochad wrapper in Python with mqtt interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aosadchyy/pymochad_mqtt",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)