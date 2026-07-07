(function(clicks, pathname) {
    if (!clicks) return window.dash_clientside.no_update;
    const context = window.dash_clientside.callback_context;
    const states = context.states_list;
    const components = [];
    states.forEach((group) => {
        if (!Array.isArray(group)) return;
        group.forEach((item) => {
            if (item.value !== undefined && item.value !== null) {
                components.push({
                    id: item.id,
                    prop: item.property,
                    value: item.value
                });
            }
        });
    });
    const endpoint = pathname;
    const payload = { page: endpoint, components: components };
    const safe = endpoint.replace(/^\/+|\/+$/g, '').replace(/\//g, '-') || 'root';
    return {
        content: JSON.stringify(payload, null, 2),
        filename: `snapshot-${safe}.json`,
        type: "application/json"
    };
})