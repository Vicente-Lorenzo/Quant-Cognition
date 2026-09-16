from __future__ import annotations

from threading import local
from datetime import datetime
from dataclasses import dataclass, field, InitVar
from typing import Any, Callable, ClassVar, Union

from Library.Utility.Datetime import utc_now
from Library.Database.Dataframe import pl
from Library.Database.Dataclass import DataclassAPI
from Library.Database.Database import DatabaseAPI, IdentityKey, ForeignKey
from Library.Utility.Typing import MISSING

@dataclass
class DatapointAPI(DataclassAPI):

    Database: ClassVar[str] = "Quant"
    Schema: ClassVar[str]
    Table: ClassVar[str]
    Enums: ClassVar[dict] = {}

    _LOADING_: ClassVar[local] = local()

    UpdatedAt: Union[datetime, None] = field(default=None, kw_only=True)
    UpdatedBy: Union[str, None] = field(default=None, kw_only=True)

    db: InitVar[Union[DatabaseAPI, None]] = field(default=None, kw_only=True)
    migrate: InitVar[bool] = field(default=False, kw_only=True)
    autosave: InitVar[bool] = field(default=False, kw_only=True)
    autoload: InitVar[bool] = field(default=False, kw_only=True)
    autooverload: InitVar[bool] = field(default=False, kw_only=True)

    _db_: Union[DatabaseAPI, None] = field(default=None, init=False, repr=False)
    _migrate_: bool = field(default=False, init=False, repr=False)
    _autosave_: bool = field(default=False, init=False, repr=False)
    _autoload_: bool = field(default=False, init=False, repr=False)
    _autooverload_: bool = field(default=False, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UpdatedAt: pl.Datetime(),
            self.ID.UpdatedBy: pl.String()
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        if self.Enums:
            for name, enumeration in self.Enums.items(): setattr(self, name, enumeration.parse(getattr(self, name)))
        self._db_, self._migrate_, self._autosave_, self._autoload_, self._autooverload_ = db, migrate, autosave, autoload, autooverload
        if self._db_ is not None:
            if self._migrate_: self._db_.migrate(schema=self.Schema, table=self.Table, structure=self.Structure)
            if self._autooverload_: self.overload()
            elif self._autoload_: self.load()

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        if self._autosave_ and name and name[0].isupper():
            try: self.save()
            except Exception as e:
                if self._db_ is not None: self._db_._log_.debug(lambda: f"Autosave {type(self).__name__}: Failed · {e}")

    @staticmethod
    def _relate_(value: Any, kind: type, normalize: Callable = MISSING, **kwargs) -> Any:
        if isinstance(value, kind): return value
        if value is MISSING or value is None: return None
        return kind(UID=normalize(value) if normalize else value, **kwargs)

    @classmethod
    def reference(cls, clause: str = MISSING) -> str:
        target = f'"{cls.Schema}"."{cls.Table}"("{cls.ID.UID}")'
        return f"{target} {clause}" if clause else target

    def primary_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if DatabaseAPI.primary(d)]

    def foreign_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if isinstance(d, ForeignKey)]

    def identity_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if isinstance(d, IdentityKey) and not getattr(d, "primary", False)]

    def natural_keys(self) -> list[str]:
        return self.primary_keys()

    def identifier(self) -> dict[str, Any]:
        data_dict = self.dict(include_fields=True, include_initvar_fields=False, include_override_fields=True, include_properties=False)
        id_keys = self.identity_keys()
        if id_keys and all(data_dict.get(k) not in (None, MISSING) for k in id_keys):
            return {k: data_dict[k] for k in id_keys}
        nat_keys = self.natural_keys()
        if nat_keys and all(data_dict.get(k) not in (None, MISSING) for k in nat_keys):
            return {k: data_dict[k] for k in nat_keys}
        return {}

    def _stamp_(self, by: str, at: Union[datetime, None] = None) -> None:
        self.UpdatedBy = by
        self.UpdatedAt = at or utc_now()

    def _push_(self, by: str) -> None:
        if self._db_ is None: return
        save_state = self._autosave_
        try:
            self._autosave_ = False
            self._stamp_(by)
            natural_key = self.natural_keys()
            identity_cols = self.identity_keys()
            data = {k: v for k, v in self.dict(include_fields=True, include_initvar_fields=False, include_properties=False, include_override_fields=True).items() if v is not None and v is not MISSING and k[0].isupper()}
            if natural_key and all(data.get(k) is not None for k in natural_key):
                insert_data = {k: v for k, v in data.items() if k not in identity_cols}
                result = self._db_.upsert(schema=self.Schema, table=self.Table, data=insert_data, key=natural_key, returning=identity_cols if identity_cols else None)
                if identity_cols and hasattr(result, "is_empty") and not result.is_empty():
                    row = result.row(0, named=True)
                    for col in identity_cols:
                        if row.get(col) is not None: setattr(self, col, row[col])
            elif identity_cols and all(data.get(k) is not None for k in identity_cols):
                update_data = {k: v for k, v in data.items() if k not in identity_cols}
                if update_data:
                    condition, parameters = self._db_.where(**{k: data[k] for k in identity_cols})
                    self._db_.update(schema=self.Schema, table=self.Table, data=update_data, condition=condition, parameters=parameters)
            else:
                fallback_key = identity_cols or natural_key or list(self.Structure.keys())[:1]
                self._db_.upsert(schema=self.Schema, table=self.Table, data=data, key=fallback_key)
        finally:
            self._autosave_ = save_state

    def save(self, by: str = "Autosave") -> None:
        self._push_(by=by)

    def _loading_(self) -> set:
        keys = getattr(self._LOADING_, "keys", None)
        if keys is None: keys = self._LOADING_.keys = set()
        return keys

    def _fetch_(self, condition: str, parameters: dict, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        loading = self._loading_()
        key = (self.Schema, self.Table, condition, tuple(sorted((str(k), str(v)) for k, v in (parameters or {}).items())))
        if key in loading: return None
        loading.add(key)
        try:
            row = self._db_.first(schema=self.Schema, table=self.Table, condition=condition, parameters=parameters)
            if row is None: return None
            save_state, self._autosave_ = self._autosave_, False
            try:
                for k, v in row.items():
                    if hasattr(self, k) and v is not None:
                        if overload or getattr(self, k) is None or getattr(self, k) is MISSING:
                            setattr(self, k, v)
            finally: self._autosave_ = save_state
            return row
        finally: loading.discard(key)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        ident = self.identifier()
        if not ident: return None
        condition, parameters = self._db_.where(**ident)
        return self._fetch_(condition=condition, parameters=parameters, overload=overload)

    def overload(self) -> Union[dict, None]:
        return self._pull_(overload=True)

    def load(self) -> Union[dict, None]:
        return self._pull_(overload=False)