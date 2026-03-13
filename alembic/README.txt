Generic single-database configuration.

This directory contains Alembic configuration for a single database.

The migration environment is configured in env.py.

The default migration script template is script.py.mako.

New migration scripts will be placed into the versions/ directory.

To generate a new migration:

    alembic revision --autogenerate -m "message"

To apply migrations:

    alembic upgrade head

To downgrade one revision:

    alembic downgrade -1

To downgrade to base:

    alembic downgrade base
