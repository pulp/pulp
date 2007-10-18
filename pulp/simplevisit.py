from turbogears.visit.api import BaseVisitManager, Visit

import logging

log = logging.getLogger("pulp.emptyvisit")

#SimpleVisitManager doesn't rely on the DB to store
#visits to the site.  We will store it in memory
class SimpleVisitManager(BaseVisitManager):
    
    def __init__(self, timeout):
        super(SimpleVisitManager,self).__init__(timeout)
        log.debug("SimpleVisitManager started")
        return

    def create_model(self):
        return

    def new_visit_with_key(self, visit_key):
        return Visit(visit_key, True)

    def visit_for_key(self, visit_key):
        return Visit(visit_key, False)

    def update_queued_visits(self, queue):
        return None
