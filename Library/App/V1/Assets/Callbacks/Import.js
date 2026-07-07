(function(contents, filename) {
    if (!contents) return window.dash_clientside.no_update;
    try {
        const parts = contents.split(',', 2);
        const b64 = parts.length > 1 ? parts[1] : parts[0];
        const json = atob(b64);
        const payload = JSON.parse(json);
        const components = payload.components || [];
        components.forEach(item => {
            if (item.id && item.prop && item.value !== undefined) {
                window.dash_clientside.set_props(item.id, {[item.prop]: item.value});
            }
        });
    } catch (e) {
        console.error("Import Snapshot: Failed to Parse", filename, e);
    }
})