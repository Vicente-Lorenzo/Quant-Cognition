import sys
import getpass
from pathlib import Path
from argparse import ArgumentParser, Namespace, SUPPRESS

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Library.Auth.Access import AccessAPI
from Library.Credential.Type import CredentialType, LayoutAPI
from Library.Credential.Credential import CredentialAPI
from Library.Credential.Vault import VaultAPI
from Library.Utility.Command import CommandAPI
from Library.Utility.Datetime import INSTANT
from Library.Utility.Typing import MISSING

class CredentialCommandAPI(CommandAPI):

    def __init__(self) -> None:
        super().__init__(name="Credential")

    @staticmethod
    def _flat_(value) -> str:
        decoded = CredentialAPI.unpack(value)
        if decoded is None: return ""
        return decoded if isinstance(decoded, str) else " · ".join(f"{name}: {item}" for name, item in decoded.items())

    @staticmethod
    def _stamp_(value) -> str:
        return value.strftime(INSTANT) if hasattr(value, "strftime") else ""

    @staticmethod
    def _role_(value: str):
        return None if value == "Owner" else value

    @classmethod
    def _shown_(cls, row: dict, vault: VaultAPI) -> dict:
        return {"Service": row.get("Service"), "Name": row.get("Name"), "Kind": row.get("Kind"), "Username": cls._flat_(row.get("Username")),
                "Secret": cls._flat_(row.get("Secret")), "Owner": row.get("Owner"), "View": AccessAPI.label(row.get("ViewRole")),
                "Edit": AccessAPI.label(row.get("EditRole")), "Access": row.get("Access"), "Validity": vault.validity(row.get("ExpiresAt")).name,
                "Expires": cls._stamp_(row.get("ExpiresAt")), "Used": cls._stamp_(row.get("UsedAt"))}

    @staticmethod
    def _prompt_(kind) -> str:
        values = {name: getpass.getpass(f"{name} (empty skips): ") for name in LayoutAPI.secrets(kind)}
        values = {name: value for name, value in values.items() if value}
        if not values: raise ValueError("Credential Secret: Failed · No value entered")
        if list(values) == [LayoutAPI.secret(kind)]: return CredentialAPI.pack(values[LayoutAPI.secret(kind)])
        return CredentialAPI.pack(values)

    @staticmethod
    def _entry_(text: str, name: str, *, mapping: bool = False):
        value = CredentialAPI.entry(text)
        if mapping and value is not None and not isinstance(value, dict): raise ValueError(f"Credential {name}: Failed · Expected a JSON object")
        return CredentialAPI.pack(value)

    @classmethod
    def _fields_(cls, args: Namespace, kind) -> dict:
        names = {"service": "Service", "name": "Name", "kind": "Kind", "expires": "ExpiresAt", "parent": "Parent", "owner": "Owner", "view_role": "ViewRole", "edit_role": "EditRole"}
        values = {column: getattr(args, name) for name, column in names.items() if hasattr(args, name)}
        if hasattr(args, "username"): values["Username"] = cls._entry_(args.username, "Username")
        if hasattr(args, "fields"): values["Fields"] = cls._entry_(args.fields, "Fields", mapping=True)
        if args.secret: values["Secret"] = cls._prompt_(kind)
        return values

    @staticmethod
    def _locate_(vault: VaultAPI, args: Namespace, by: str) -> str:
        if args.uid: return args.uid
        if not args.service or not args.name: raise ValueError("Credential Target: Failed · Name the credential by --uid or by --service and --name")
        rows = [row for row in vault.credentials(by=by, service=args.service) if row["Name"] == args.name]
        if not rows: raise LookupError(f"Credential Target: Failed · {args.service} · {args.name} not found")
        return rows[0]["UID"]

    @staticmethod
    def _targeted_(parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument("--uid", default=None)
        parser.add_argument("--service", default=None)
        parser.add_argument("--name", default=None)
        return parser

    @classmethod
    def _described_(cls, parser: ArgumentParser, default) -> None:
        roles = "{" + ",".join(["Owner", *AccessAPI.roles()]) + "}"
        parser.add_argument("--kind", default=default, choices=CredentialType.names())
        parser.add_argument("--username", default=default)
        parser.add_argument("--secret", action="store_true")
        parser.add_argument("--fields", default=default)
        parser.add_argument("--expires", default=default, metavar=INSTANT.replace("%", ""))
        parser.add_argument("--parent", default=default, metavar="UID")
        parser.add_argument("--owner", default=default)
        parser.add_argument("--view-role", type=cls._role_, default=default, metavar=roles)
        parser.add_argument("--edit-role", type=cls._role_, default=default, metavar=roles)

    def arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
        parser.add_argument("--user", default=MISSING)
        action = parser.add_subparsers(dest="action", required=True)
        action.add_parser("list").add_argument("--service", default=None)
        action.add_parser("due").add_argument("--margin", type=int, default=MISSING)
        for name in ("show", "delete", "reveal"): self._targeted_(action.add_parser(name))
        store = action.add_parser("store")
        store.add_argument("--service", required=True)
        store.add_argument("--name", required=True)
        self._described_(store, None)
        update = self._targeted_(action.add_parser("update"))
        update.add_argument("--rename", default=SUPPRESS)
        self._described_(update, SUPPRESS)
        transfer = self._targeted_(action.add_parser("transfer"))
        transfer.add_argument("--to", required=True)

    def run(self, args: Namespace) -> int:
        vault = VaultAPI(database=args.database)
        by = args.user or vault.administrator()
        match args.action:
            case "list": self.table([self._shown_(row, vault) for row in vault.credentials(by=by, service=args.service or MISSING)])
            case "due":
                due = {row["UID"] for row in vault.due(margin=args.margin)}
                self.table([self._shown_(row, vault) for row in vault.credentials(by=by) if row["UID"] in due])
            case "show":
                row = vault.credential(self._locate_(vault, args, by), by=by)
                if row is None: raise PermissionError("Credential Show: Failed · You may not view this credential")
                self.detail(self._shown_(row, vault))
            case "store":
                credential = vault.store(by=by, **{key: value for key, value in self._fields_(args, args.kind or CredentialType.Password.name).items() if value is not None or key in ("ViewRole", "EditRole")})
                print(f"Credential '{credential.Service} · {credential.Name}' stored · {credential.UID}")
            case "update":
                uid = self._locate_(vault, args, by)
                current = vault.credential(uid, by=by)
                values = self._fields_(args, getattr(args, "kind", None) or (current or {}).get("Kind"))
                if hasattr(args, "rename"): values["Name"] = args.rename
                else: values.pop("Name", None)
                values.pop("Service", None)
                if vault.update(uid, by=by, **values) is None: raise PermissionError("Credential Update: Failed · You may not edit this credential")
                print(f"Credential '{uid}' updated")
            case "delete":
                if not vault.delete(self._locate_(vault, args, by), by=by): raise PermissionError("Credential Delete: Failed · You may not delete this credential")
                print("Credential deleted")
            case "transfer":
                if not vault.transfer(self._locate_(vault, args, by), args.to, by=by): raise PermissionError("Credential Transfer: Failed · You may not edit this credential")
                print(f"Credential transferred to {args.to}")
            case "reveal":
                values = vault.reveal(self._locate_(vault, args, by), by=by)
                if values is None: raise PermissionError("Credential Reveal: Failed · You may not reveal this credential")
                self.detail(values)
        return 0

if __name__ == "__main__":
    raise SystemExit(CredentialCommandAPI().main())