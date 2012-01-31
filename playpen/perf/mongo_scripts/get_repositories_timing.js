db = connect("localhost:27017/pulp_database")

var startDate = "2012-01-13T13:22:00Z";
var endDate = "2012-01-13T13:23:08Z";


result = db.system.profile.find(
    {
        info: /repos/,
        ts: {
            $gt:new ISODate(startDate),
            $lt:new ISODate(endDate)
        }
    }).sort({millis:-1});
result.forEach(printjson);
