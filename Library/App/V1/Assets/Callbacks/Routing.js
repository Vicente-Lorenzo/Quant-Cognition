(function(nav) {
    if (!nav) return window.dash_clientside.no_update;
    const { href, external, refresh } = nav;
    if (!external && !refresh) {
        window.history.pushState({}, "", href);
        window.dispatchEvent(new PopStateEvent("popstate"));
        return;
    }
    const target = external ? "_blank" : "_self";
    const features = external ? "noopener,noreferrer" : "";
    window.open(href, target, features);
})