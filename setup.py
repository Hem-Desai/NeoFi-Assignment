from setuptools import setup, find_packages

setup(
    name="neofi-event-management",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "alembic",
        "python-jose",
        "passlib",
        "python-multipart",
        "msgpack"
    ],
) 