function orphanReduce(key, values) {
    var total = 0;
    for (var i=0; i < values.length; i++) {
        total += values[i].count;
    }
    return {package_id:key, count: total};
}
