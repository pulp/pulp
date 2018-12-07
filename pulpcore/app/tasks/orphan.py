from pulpcore.app.models import Artifact, Content, ContentArtifact, ProgressBar, RepositoryContent


def orphan_cleanup():
    """
    Delete all orphan Content and Artifact records.
    This task removes Artifact files from the filesystem as well.
    """
    # Content cleanup
    content = Content.objects.exclude(pk__in=RepositoryContent.objects.values_list('content_id',
                                                                                   flat=True))
    progress_bar = ProgressBar(message='Clean up orphan Content', total=content.count(),
                               done=0, state='running')
    progress_bar.save()
    content.delete()
    progress_bar.done = progress_bar.total
    progress_bar.state = 'completed'
    progress_bar.save()

    # Artifact cleanup
    artifacts = Artifact.objects.exclude(pk__in=ContentArtifact.objects.values_list('artifact_id',
                                                                                    flat=True))
    progress_bar = ProgressBar(message='Clean up orphan Artifacts', total=artifacts.count(),
                               done=0, state='running')
    progress_bar.save()
    for artifact in artifacts:
        # we need to manually call delete() because it cleans up the file on the filesystem
        artifact.delete()
        progress_bar.increment()

    progress_bar.state = 'completed'
    progress_bar.save()
