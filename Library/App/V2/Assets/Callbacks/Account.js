(function(user) {
    var authed = !!(user && user.name);
    var role = (authed ? (user.role || "Editor") : "Public").toLowerCase();
    var icon = authed ? "bi bi-person-check-fill" : "bi bi-person";
    return [
        icon + " app-account-icon app-account-" + role,
        authed ? user.name : "Guest",
        authed ? "bi bi-box-arrow-right" : "bi bi-box-arrow-in-right",
        authed ? "Sign Out" : "Sign In"
    ];
})