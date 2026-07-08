(function(hash) {
    var map = {"#appearance": "appearance", "#session": "session", "#storage": "storage"};
    if (hash && map[hash]) return map[hash];
    return window.dash_clientside.no_update;
})