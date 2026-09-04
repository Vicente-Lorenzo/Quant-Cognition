from dash import dcc, html
from dataclasses import dataclass, field

from Library.App.V2.Component.Component import Component, ComponentAPI

@dataclass(kw_only=True)
class CrumbAPI:

    label: str
    href: str = None

    @classmethod
    def resolve(cls, entry) -> "CrumbAPI":
        if isinstance(entry, CrumbAPI): return entry
        if isinstance(entry, (tuple, list)): return cls(label=str(entry[0]), href=entry[1] if len(entry) > 1 else None)
        return cls(label=str(entry))

@dataclass(kw_only=True)
class BreadcrumbAPI(ComponentAPI):

    classname: str = "breadcrumb-trail"
    builder: type[Component] = html.Nav

    trail: list = field(default_factory=list)
    separator: str = "›"

    def crumbs(self) -> list:
        return [CrumbAPI.resolve(entry) for entry in self.trail if entry is not None]

    def build(self) -> list[Component]:
        crumbs = self.crumbs()
        elements = []
        for index, crumb in enumerate(crumbs):
            if index: elements.append(html.Span(self.separator, className="crumb-separator"))
            last = index == len(crumbs) - 1
            if crumb.href and not last: elements.append(dcc.Link(crumb.label, href=crumb.href, className="crumb"))
            else: elements.append(html.Span(crumb.label, className="crumb crumb-current" if last else "crumb"))
        return self.serialize([self.builder(elements, **self.arguments())])