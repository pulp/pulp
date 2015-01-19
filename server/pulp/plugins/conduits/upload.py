from pulp.plugins.conduits.mixins import (
    AddUnitMixin, SingleRepoUnitsMixin, SearchUnitsMixin,
    ImporterConduitException)


class UploadConduit(AddUnitMixin, SingleRepoUnitsMixin, SearchUnitsMixin):

    def __init__(self, repo_id, importer_id, association_owner_type,
                 association_owner_id):
        AddUnitMixin.__init__(self, repo_id, importer_id,
                              association_owner_type, association_owner_id)
        SingleRepoUnitsMixin.__init__(self, repo_id, ImporterConduitException)
        SearchUnitsMixin.__init__(self, ImporterConduitException)
