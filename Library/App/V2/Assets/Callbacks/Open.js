(function(clicks, state) {
    var nu = window.dash_clientside.no_update;
    if (!state || !state.base || !state.selected || !state.selected.length) return nu;
    var base = String(state.base).replace(/\/+$/, "");
    var uids = state.selected;
    if (uids.length === 1) return base + "/" + encodeURIComponent(uids[0]);
    var blocked = 0;
    for (var index = 1; index < uids.length; index++) {
        var opened = window.open(base + "/" + encodeURIComponent(uids[index]), "_blank");
        if (!opened || opened.closed || typeof opened.closed === "undefined") blocked++;
    }
    if (blocked) {
        var note = document.createElement("div");
        note.className = "app-popup-hint";
        note.textContent = "Your browser blocked " + blocked + " of " + (uids.length - 1) + " extra tabs \u00b7 allow pop-ups for this site to open every selection at once";
        document.body.appendChild(note);
        setTimeout(function() { note.remove(); }, 8000);
    }
    return base + "/" + encodeURIComponent(uids[0]);
})