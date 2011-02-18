function orphanMap() {
    var a = db.repos.find({"packages":this.id}, {"id":1});
    if (a.count() == 0) {
        emit(this.id, {count:a.count()})
    }
}
