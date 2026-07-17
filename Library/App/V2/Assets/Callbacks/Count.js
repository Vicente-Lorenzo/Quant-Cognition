(function(data, viewport, selected) {
    var total = (data || []).length;
    var page = (viewport || []).length;
    var chosen = (selected || []).length;
    return total + " total · " + page + " on page · " + chosen + " selected";
})