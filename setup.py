from setuptools import setup, find_packages

setup(
    name="data-factory",
    version="1.0.0",
    author="Valko",
    author_email="valensantarone@gmail.com",
    description="Scrape football data from DataFactory",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://www.github.com/valensantarone/datafactory",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pandas",
        "numpy"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    package_data={
        'datafactory': ['data/xTGrid.json'],
    },
)