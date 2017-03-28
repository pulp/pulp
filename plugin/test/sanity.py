import os

from urllib.parse import urljoin
from mock import patch, Mock

from pulp.download import HttpDownload, SizeValidation, DigestValidation
from pulp.plugin import RemoteArtifact, RemoteContent, ChangeSet, ChangeReport, SizedIterator


# ------------------- FAKE MODEL ---------------------------------------


class QuerySet(tuple):

    def only(self, *args):
        return self


class Manager:

    @staticmethod
    def get(**kwargs):
        raise Model.DoesNotExist()

    @staticmethod
    def filter(*args, **kwargs):
        print('filter: {}{}', args, kwargs)
        return QuerySet()

    @staticmethod
    def delete(**kwargs):
        print('delete: {}', kwargs)


class ContentManager(Manager):

    existing = []

    @staticmethod
    def get(**kwargs):
        print('get(): {}{}', kwargs)
        try:
            return QuerySet(ContentManager.existing[0],)
        except IndexError:
            raise Model.DoesNotExist()

    @staticmethod
    def filter(*args, **kwargs):
        print('filter(): {}{}', args, kwargs)
        existing = ContentManager.existing
        return QuerySet(tuple(existing))


class Model:

    class DoesNotExist(Exception):
        pass

    objects = Manager()

    def __init__(self, model_id=''):
        self.id = model_id

    def save(self):
        print('{} - saved'.format(self.id))

    def delete(self):
        print('{} - deleted'.format(self.id))

    def __repr__(self):
        return self.id


class Content(Model):

    objects = ContentManager()

    NEXT_ID = 0
    TYPE = ''

    natural_key_fields = ()

    def __init__(self):
        super(Content, self).__init__('C{}'.format(Content.NEXT_ID))
        self.artifacts = []
        self.type = self.TYPE
        Content.NEXT_ID += 1

    def natural_key(self):
        return tuple()


class Artifact(Model):

    NEXT_ID = 0

    def __init__(self, content, relative_path=None):
        super(Artifact, self).__init__('A{}'.format(Artifact.NEXT_ID))
        self.content = content
        self.relative_path = relative_path
        self.file = None
        self.size = 0
        self.md5 = ''
        self.downloaded = False
        Artifact.NEXT_ID += 1
        content.artifacts.append(self)


class Importer(Model):

    NEXT_ID = 0

    def __init__(self):
        super(Importer, self).__init__('I{}'.format(Importer.NEXT_ID))
        Importer.NEXT_ID += 1
        self.repository = Repository()
        self.ssl_ca_certificate = 'ca.pem'
        self.ssl_client_certificate = 'client.pem'
        self.ssl_client_key = 'key.pem'
        self.feed_url = 'http://testing.org/content'
        self.proxy_url = 'http://safety.org'
        self.download_policy = False
        self.headers = None

    def sync(self):
        raise NotImplementedError()

    def get_artifact_download(self, artifact, url, destination):
        """
        Build an artifact download object.

        Args:
            artifact (Artifact): The associated artifact.
            url (str): The download URL.
            destination (str): The absolute path to where the downloaded file is to be stored.

        Returns:
            pulp3.download.Download: The appropriate download.
        """
        download = HttpDownload(url, destination)
        download.ssl_ca_certificate = self.ssl_ca_certificate
        download.ssl_client_certificate = self.ssl_client_certificate
        download.ssl_client_key = self.ssl_client_key
        download.proxy_url = self.proxy_url
        download.headers = self.headers
        if artifact.size:
            validation = SizeValidation(artifact.size)
            download.validations.append(validation)
        for algorithm in DigestValidation.ALGORITHMS:
            try:
                digest = getattr(artifact, algorithm)
                if not digest:
                    continue
            except AttributeError:
                continue
            else:
                validation = DigestValidation(algorithm, digest)
                download.validations.append(validation)
                break
        return download


class Repository(Model):

    NEXT_ID = 0

    def __init__(self):
        super(Repository, self).__init__('R{}'.format(Repository.NEXT_ID))
        Repository.NEXT_ID += 1


class RepositoryContent(Model):

    NEXT_ID = 0

    def __init__(self, repository, content):
        super(RepositoryContent, self).__init__('[C/R]{}'.format(RepositoryContent.NEXT_ID))
        self.repository = repository
        self.content = content
        RepositoryContent.NEXT_ID += 1


class DownloadCatalog(Model):

    NEXT_ID = 0

    def __init__(self, url='', artifact=None, importer=None):
        super(DownloadCatalog, self).__init__('CAT{}'.format(DownloadCatalog.NEXT_ID))
        self.url = url
        self.artifact = artifact
        self.importer = importer
        DownloadCatalog.NEXT_ID += 1


class ProgressBar(Model):

    def __init__(self, message, total):
        super(ProgressBar, self).__init__('')
        self.message = message
        self.total = total
        self.completed = 0

    def increment(self):
        self.completed += 1
        print('{} {}/{}'.format(self.message, self.completed, self.total))

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        pass


class Task:

    @staticmethod
    def append_non_fatal_error(error):
        print('ERROR: "{}" appended', error)


# --------------------------- CONTENT ----------------------------------


class Thing(Content):
    """
    Imaginary content.
    """

    def __init__(self, name, version='1.0', release='1'):
        super(Thing, self).__init__()
        self.name = name
        self.version = version
        self.release = release

    type = 'Thing'

    natural_key_fields = ('name', 'version', 'release')

    def natural_key(self):
        return tuple(getattr(self, f) for f in self.natural_key_fields)


# ----------------------------- IMPORTER -------------------------------

# Testing
# Faked existing content
Thing.objects.existing += [
    Thing(name='thing{}'.format(n)) for n in [2, 4, 6]
]


class ThingImporter(Importer):
    """
    Assumes the Importer.working_dir.
      - The ssl_* settings are paths instead of actual certificate PEM.
      - Plugin writer not concerned with whether the content already exists
        and only needs to be associated.  Determined by ChangeSet.
      - Deferred catalog managed with delta and not recreated each time. Will need
        a way to refresh the catalog without attempting to re-associate everything.
    """

    working_dir = '/tmp/working'  # placeholder

    def sync(self):
        # Determine needed changes to the repository.
        wanted = self._find_wanted()
        unwanted = self._find_unwanted()

        # Create the changeset and apply it.
        changeset = ChangeSet(self, adds=wanted, deletes=unwanted)
        result = changeset.apply()

        # Let's inspect the reports
        added = 0
        deleted = 0
        for report in result:
            print('CHANGE-REPORT: ({}) {}'.format(report.action, report.content))
            if report.action == ChangeReport.ADDED:
                added += 1
            if report.action == ChangeReport.DELETED:
                deleted += 1
        print('Added: {}/{}'.format(added, len(wanted)))
        print('Deleted: {}/{}'.format(deleted, len(unwanted)))

        # Report based on how many failed.
        failed = len(wanted) - added
        if failed:
            raise Exception('{} failed :-('.format(failed))

        failed = len(unwanted) - deleted
        if failed:
            raise Exception('{} failed :-('.format(failed))

    def _find_wanted(self, n=10):
        def build_wanted():
            for _id in range(n):
                content = RemoteContent(Thing(name='thing{}'.format(_id)))
                if _id % 2 == 0:
                    # only even content (id) has artifacts
                    for a in range(3):
                        rel_path = 'file{}'.format(a)
                        artifact = Artifact(content=content.model, relative_path=rel_path)
                        url = urljoin(self.feed_url, os.path.join('packages', rel_path))
                        destination = os.path.join(self.working_dir, rel_path)
                        download = self.get_artifact_download(artifact, url, destination)
                        download.url = 'file://{}'.format(__file__)
                        content.add_artifact(RemoteArtifact(artifact, download))
                yield content
        return SizedIterator(n, build_wanted())

    def _find_unwanted(self, n=3):
        def build_unwanted():
            for content in (Thing(name='thing{}'.format(_)) for _ in range(n)):
                for x in range(3):
                    Artifact(content=content)
                yield content
        return SizedIterator(n, build_unwanted())


# --------------------------- TEST -------------------------------------

def reset():
    Content.NEXT_ID = 0
    Artifact.NEXT_ID = 0
    Repository.NEXT_ID = 0
    RepositoryContent.NEXT_ID = 0
    Importer.NEXT_ID = 0


@patch('pulp.plugin.changeset.open', Mock())
@patch('pulp.plugin.changeset.File', Mock())
@patch('pulp.plugin.changeset.Task', Task)
@patch('pulp.plugin.changeset.ProgressBar', ProgressBar)
@patch('pulp.plugin.changeset.DownloadCatalog', DownloadCatalog)
@patch('pulp.plugin.changeset.RepositoryContent', RepositoryContent)
def main():
    for policy in ('immediate', 'background'):
        reset()
        importer = ThingImporter()
        print('------ POLICY={} ------'.format(policy.upper()))
        importer.download_policy = policy
        importer.sync()


if __name__ == '__main__':
    main()
