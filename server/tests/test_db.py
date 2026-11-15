import pytest


@pytest.mark.db
def test_schema_cria_tabelas(db):
    tabelas = {
        r[0]
        for r in db.execute(
            "select tablename from pg_tables where schemaname='public'"
        ).fetchall()
    }
    assert {"chunks", "usage"} <= tabelas


@pytest.mark.db
def test_chunks_tem_vetor_1024(db):
    tipo = db.execute(
        "select format_type(atttypid, atttypmod) from pg_attribute "
        "where attrelid='chunks'::regclass and attname='embedding'"
    ).fetchone()[0]
    assert tipo == "vector(1024)"
