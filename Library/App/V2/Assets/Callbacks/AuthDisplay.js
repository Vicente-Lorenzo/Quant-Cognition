(function(user) {
    var authed = !!(user && user.name);
    return authed ? ["bi bi-box-arrow-right", "Sign Out"] : ["bi bi-box-arrow-in-right", "Sign In"];
})