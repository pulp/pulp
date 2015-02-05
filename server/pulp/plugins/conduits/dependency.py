from pulp.plugins.conduits.mixins import (ImporterScratchPadMixin, RepoScratchPadMixin,
                                          SingleRepoUnitsMixin, ImporterConduitException)


class DependencyResolutionConduit(RepoScratchPadMixin, ImporterScratchPadMixin,
                                  SingleRepoUnitsMixin):

    def __init__(self, repo_id, importer_id):
        RepoScratchPadMixin.__init__(self, repo_id, ImporterConduitException)
        ImporterScratchPadMixin.__init__(self, repo_id, importer_id)
        SingleRepoUnitsMixin.__init__(self, repo_id, ImporterConduitException)
