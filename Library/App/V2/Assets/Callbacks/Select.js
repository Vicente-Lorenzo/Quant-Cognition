(function(rows, data) {
    if (!rows || !data) return [];
    var uids = [];
    for (var index = 0; index < rows.length; index++) {
        var row = data[rows[index]];
        if (row && row.UID !== null && row.UID !== undefined) uids.push(row.UID);
    }
    return uids;
})