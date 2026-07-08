(function(clicks, open, cls) {
    if (!clicks) return window.dash_clientside.no_update;
    const newOpen = !open;
    if (cls === undefined) return newOpen;
    const newCls = newOpen ? cls.replace("down", "up") : cls.replace("up", "down");
    return [newOpen, newCls];
})