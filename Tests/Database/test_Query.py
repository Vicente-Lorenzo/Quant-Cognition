import pytest
from Library.Database.Query import QueryAPI
from Library.Database.Oracle import OracleDatabaseAPI
from Library.Database.Postgres import PostgresDatabaseAPI
def test_interpolation():
    q = QueryAPI("SELECT * FROM ::schema::.::table::")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, schema="public", table="users")
    assert query == "SELECT * FROM public.users"
    assert configuration == []
    assert parameters is None
def test_missing_interpolation():
    q = QueryAPI("SELECT * FROM ::schema::.t")
    with pytest.raises(KeyError): q(PostgresDatabaseAPI._PARAMETER_TOKEN_)
def test_interpolation_and_named_same_key():
    q = QueryAPI("SELECT * FROM ::x::.t WHERE x = :x:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, x="public")
    assert query == "SELECT * FROM public.t WHERE x = %s"
    assert configuration == ["x"]
    assert parameters == ("public",)
def test_positional():
    q = QueryAPI("SELECT * FROM t WHERE a = :?: AND b = :?:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, 10, 20)
    assert query == "SELECT * FROM t WHERE a = %s AND b = %s"
    assert configuration == [0, 1]
    assert parameters == (10, 20)
def test_named_compiles_to_positional():
    q = QueryAPI("SELECT * FROM t WHERE id = :id: AND s = :status:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, id=7, status="ACTIVE")
    assert query == "SELECT * FROM t WHERE id = %s AND s = %s"
    assert configuration == ["id", "status"]
    assert parameters == (7, "ACTIVE")
def test_named_and_positional_ordering():
    q = QueryAPI("SELECT * FROM t WHERE id = :id: AND s = :?: AND x = :x:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, "SVAL", id=1, x=3)
    assert query == "SELECT * FROM t WHERE id = %s AND s = %s AND x = %s"
    assert configuration == ["id", 0, "x"]
    assert parameters == (1, "SVAL", 3)
def test_duplicate_named_parameter():
    q = QueryAPI("SELECT * FROM t WHERE a = :id: OR b = :id:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, id=99)
    assert query == "SELECT * FROM t WHERE a = %s OR b = %s"
    assert configuration == ["id", "id"]
    assert parameters == (99, 99)
def test_interpolation_and_named():
    q = QueryAPI("SELECT * FROM ::schema::.::table:: WHERE id = :id:")
    query, configuration, parameters = q(PostgresDatabaseAPI._PARAMETER_TOKEN_, schema="public", table="users", id=5)
    assert query == "SELECT * FROM public.users WHERE id = %s"
    assert configuration == ["id"]
    assert parameters == (5,)
def test_missing_positional():
    q = QueryAPI("SELECT * FROM t WHERE a = :?: AND b = :?:")
    with pytest.raises(ValueError): q(PostgresDatabaseAPI._PARAMETER_TOKEN_, 10)
def test_missing_named():
    q = QueryAPI("SELECT * FROM t WHERE id = :id:")
    with pytest.raises(KeyError): q(PostgresDatabaseAPI._PARAMETER_TOKEN_)
def test_numbered_placeholders():
    q = QueryAPI("SELECT * FROM t WHERE a = :?: AND b = :x: AND c = :?:")
    query, configuration, parameters = q(OracleDatabaseAPI._PARAMETER_TOKEN_, "A", "C", x="B")
    assert query == "SELECT * FROM t WHERE a = :1 AND b = :2 AND c = :3"
    assert configuration == [0, "x", 1]
    assert parameters == ("A", "B", "C")