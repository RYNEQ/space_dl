import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="space_dl",
    version="0.1.0",
    author="Ariyan Eghbal",
    author_email="ariyan.eghbal@gmail.com",
    description="Download Twitter Space",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RYNEQ/space_dl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: CC License",
        "Operating System :: OS Independent",
    ],
    setup_requires=['ffmpeg-python', 'm3u8', 'pymediainfo', 'requests']
)