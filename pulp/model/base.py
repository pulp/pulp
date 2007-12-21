from suds.property import Property

class PageControl(Property):
    def __init__(self):
        Property.__init__(self)
        #super(PageControl).__init__()
        self.pageNumber = 0
        self.pageSize = 100


