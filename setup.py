from setuptools import setup, find_packages

setup(
    name='walmart_lib',
    version='0.1',
    author='Samuel Benning',
    author_email='bensam1993@gmail.com',
    description='A Python library for interacting with Walmart API',
    packages=find_packages(),
    install_requires=[
        "httpx",
        "pydantic"
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6'
)