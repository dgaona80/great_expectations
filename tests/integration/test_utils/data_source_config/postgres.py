from random import randint
from typing import Mapping, Union

import pandas as pd
import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, insert

# commented out types are present in SqlAlchemy 2.x but not 1.4
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    BIGINT,
    BIT,
    BOOLEAN,
    BYTEA,
    CHAR,
    CIDR,
    # CITEXT,
    DATE,
    # DATEMULTIRANGE,
    DATERANGE,
    # DOMAIN,
    DOUBLE_PRECISION,
    ENUM,
    FLOAT,
    HSTORE,
    INET,
    # INT4MULTIRANGE,
    INT4RANGE,
    # INT8MULTIRANGE,
    INT8RANGE,
    INTEGER,
    INTERVAL,
    JSON,
    JSONB,
    # JSONPATH,
    MACADDR,
    # MACADDR8,
    MONEY,
    NUMERIC,
    # NUMMULTIRANGE,
    NUMRANGE,
    OID,
    REAL,
    REGCLASS,
    # REGCONFIG,
    SMALLINT,
    TEXT,
    TIME,
    TIMESTAMP,
    # TSMULTIRANGE,
    # TSQUERY,
    # TSRANGE,
    # TSTZMULTIRANGE,
    TSTZRANGE,
    TSVECTOR,
    UUID,
    VARCHAR,
)

from great_expectations.compatibility.typing_extensions import override
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.test_utils.data_source_config.base import (
    BatchTestSetup,
    DataSourceTestConfig,
)

# Sqlalchemy follows the convention of exporting all known valid types for a given dialect
# as uppercase types from the namespace `sqlalchemy.dialects.<dialect>
# commented out types are present in SqlAlchemy 2.x but not 1.4
PostgresColumnType = Union[
    type[ARRAY],
    type[BIGINT],
    type[BIT],
    type[BOOLEAN],
    type[BYTEA],
    type[CHAR],
    type[CIDR],
    # type[CITEXT],
    type[DATE],
    # type[DATEMULTIRANGE],
    type[DATERANGE],
    # type[DOMAIN],
    type[DOUBLE_PRECISION],
    type[ENUM],
    type[FLOAT],
    type[HSTORE],
    type[INET],
    # type[INT4MULTIRANGE],
    type[INT4RANGE],
    # type[INT8MULTIRANGE],
    type[INT8RANGE],
    type[INTEGER],
    type[INTERVAL],
    type[JSON],
    type[JSONB],
    # type[JSONPATH],
    type[MACADDR],
    # type[MACADDR8],
    type[MONEY],
    type[NUMERIC],
    # type[NUMMULTIRANGE],
    type[NUMRANGE],
    type[OID],
    type[REAL],
    type[REGCLASS],
    # type[REGCONFIG],
    type[SMALLINT],
    type[TEXT],
    type[TIME],
    type[TIMESTAMP],
    # type[TSMULTIRANGE],
    # type[TSQUERY],
    # type[TSRANGE],
    # type[TSTZMULTIRANGE],
    type[TSTZRANGE],
    type[TSVECTOR],
    type[UUID],
    type[VARCHAR],
]


class PostgreSQLDatasourceTestConfig(DataSourceTestConfig[PostgresColumnType]):
    @property
    @override
    def label(self) -> str:
        return "postgresql"

    @property
    @override
    def pytest_mark(self) -> pytest.MarkDecorator:
        return pytest.mark.postgresql

    @override
    def create_batch_setup(
        self,
        request: pytest.FixtureRequest,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
    ) -> BatchTestSetup:
        return PostgresBatchTestSetup(
            data=data,
            config=self,
            extra_data=extra_data,
        )


class PostgresBatchTestSetup(BatchTestSetup[PostgreSQLDatasourceTestConfig]):
    def __init__(
        self,
        config: PostgreSQLDatasourceTestConfig,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
    ) -> None:
        self.table_name = f"postgres_expectation_test_table_{randint(0, 1000000)}"
        self.connection_string = "postgresql+psycopg2://postgres@localhost:5432/test_ci"
        self.engine = create_engine(url=self.connection_string)
        self.metadata = MetaData()
        self.tables: Union[list[Table], None] = None
        self.schema = "public"
        self.extra_data = extra_data
        super().__init__(config=config, data=data)

    @override
    def make_batch(self) -> Batch:
        name = self._random_resource_name()
        return (
            self._context.data_sources.add_postgres(
                name=name, connection_string=self.connection_string
            )
            .add_table_asset(
                name=name,
                table_name=self.table_name,
                schema_name=self.schema,
            )
            .add_batch_definition_whole_table(name=name)
            .get_batch()
        )

    @override
    def setup(self) -> None:
        main_table = self._create_table(name=self.table_name, columns=self.get_column_types())
        extra_tables = {
            table_name: self._create_table(
                name=table_name,
                columns=self.get_extra_column_types(table_name),
            )
            for table_name in self.extra_data
        }
        self.tables = [main_table, *extra_tables.values()]

        self.metadata.create_all(self.engine)
        with self.engine.connect() as conn:
            # pd.DataFrame(...).to_dict("index") returns a dictionary where the keys are the row
            # index and the values are a dict of column names mapped to column values.
            # Then we pass that list of dicts in as parameters to our insert statement.
            #   INSERT INTO test_table (my_int_column, my_str_column) VALUES (?, ?)
            #   [...] [('1', 'foo'), ('2', 'bar')]
            with conn.begin():
                conn.execute(insert(main_table), list(self.data.to_dict("index").values()))
                for table_name, table_data in self.extra_data.items():
                    conn.execute(
                        insert(extra_tables[table_name]),
                        list(table_data.to_dict("index").values()),
                    )

    @override
    def teardown(self) -> None:
        if self.tables:
            for table in self.tables:
                table.drop(self.engine)

    def _create_table(self, name: str, columns: Mapping[str, PostgresColumnType]) -> Table:
        column_list = [Column(col_name, col_type) for col_name, col_type in columns.items()]
        return Table(name, self.metadata, *column_list, schema=self.schema)

    def get_column_types(self) -> Mapping[str, PostgresColumnType]:
        if self.config.column_types is None:
            return {}
        return self.config.column_types

    def get_extra_column_types(self, table_name: str) -> Mapping[str, PostgresColumnType]:
        extra_assets = self.config.extra_assets
        if not extra_assets:
            return {}
        else:
            return extra_assets[table_name]
