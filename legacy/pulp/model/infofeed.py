import logging

log = logging.getLogger("pulp.model.infofeed")


class InfoFeedService:
        
    #get a feed for a person
    def get_perspective_feed(self, identity):
        log.debug("get_feed called")
        ret = []
        e1 = """
            12 new errata issued for channel RHEL4 AS.
            3 of these are security errata.
            """
        e2 = "RHEL4 AS channel modified by user chewbacca"
        e3 = "2 new channels created by user dvader"
        e4 = "1 new channel created by user msmithy"
        ret.append(InfoItem(0, "Software Updates", e1, "Today 2:13 PM"))
        ret.append(InfoItem(0, "Software Content", e2, "Yesterday 5:37 PM"))
        ret.append(InfoItem(0, "Software Content", e3, "Yesterday 7:44 AM"))
        ret.append(InfoItem(0, "Software Content", e4, "June 7 7:44 AM"))
        return ret  

    #get a feed for a person
    def get_virt_feed(self, identity):
        log.debug("get_feed called")
        ret = []
        e1 = "4 virtual sytems restarted"
        e2 = "RHEL4 AS I386 Provisioning Distribution created by user ccannon."
        e3 = "1 Virtual Host Pool created by user admin33"
        e4 = "120 virtual systems provisioned into Production Host Pool by user rroot"
        e5 = "1 Fedora 8 Provisioning Profile created by user admin33"
        ret.append(InfoItem(0, None, e1, "Today 2:13 PM"))
        ret.append(InfoItem(0, None, e2, "Yesterday 5:37 PM"))
        ret.append(InfoItem(0, None, e3, "Yesterday 7:44 AM"))
        ret.append(InfoItem(0, None, e4, "June 7 7:44 AM"))
        ret.append(InfoItem(0, None, e4, "June 1 6:34 AM"))
        return ret  


class InfoItem:
    def __init__(self, id, perspective, event, date):
        self.id = id
        self.perspective = perspective
        self.event = event
        self.date = date

