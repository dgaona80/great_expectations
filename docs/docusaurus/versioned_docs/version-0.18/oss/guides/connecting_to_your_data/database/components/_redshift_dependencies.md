import SqlAlchemy2 from '../../../../../components/warnings/_sql_alchemy2.md'

To use connect to your Redshift database, Great Expectations will require the installation of additional dependencies.  Fortunately, it is simple to install the necessary dependencies for Redshift by using `pip` and running the following from your terminal:

```console title="Terminal input"
pip install sqlalchemy sqlalchemy-redshift psycopg2

# or if on macOS:
pip install sqlalchemy sqlalchemy-redshift psycopg2-binary
```

<SqlAlchemy2 />
