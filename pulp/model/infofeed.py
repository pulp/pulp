class InfoFeedService:
        
    #get a feed for a person
    def get_feed(self, identity): 
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

class InfoItem:
    def __init__(self, id, perspective, event, date):
        self.id = id
        self.perspective = perspective
        self.event = event
        self.date = date

