(function(hash) {
    var map = {"#appearance": "appearance", "#security": "security", "#session": "session"};
    if (hash && map[hash]) return map[hash];
    return window.dash_clientside.no_update;
})