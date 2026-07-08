(function(user) {
    var authed = !!user;
    return [
        authed ? "bi bi-lock-fill app-lock app-lock-authed" : "bi bi-unlock app-lock app-lock-guest",
        authed ? user : "Guest",
        authed ? "bi bi-box-arrow-right" : "bi bi-box-arrow-in-right",
        authed ? "Sign Out" : "Sign In"
    ];
})