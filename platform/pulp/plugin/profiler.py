class Profiler(object):
    """
    The base profiler class to answer applicability questions regarding updates.

    This is meant to be subclassed by plugin authors who wish to provide the applicability
    feature set. The plugin implementation returns a list of plugin subclassed
    :class: `~pulp.plugin.ContentUnit` objects. Those objects are in the repo and are applicable
    for the unit_profile.

    See :meth: `Profiler.calculate_applicable_units` for more info.

    :ivar repo: The repository to be used to calculate applicability against the given
                consumer profile.
    :type repo: :class: `pulp.plugin.Repository`
    """

    def __init__(self, repo):
        """
        Initialize with a :class: `pulp.plugin.Repository` object

        :param repo: The repository to be used to calculate applicability against the given
                     consumer profile.
        :type repo: :class: `pulp.plugin.Repository`
        """
        self.repo = repo

    def calculate_applicable_units(self, unit_profile):
        """
        Return the applicable units for unit_profile

        Calculate and return a list of subclasses of :class: `~pulp.plugin.ContentUnit`
        applicable to consumers with given 'unit_profile'. Applicability is calculated against all
        content units belonging to the associated repository. The definition of "applicable" is
        content type specific and up to the subclassed implementation.

        :param unit_profile: The consumer unit profile
        :type unit_profile: dict

        :return: a list of applicable :class: `~pulp.plugin.ContentUnit` objects
        :rtype: list of :class: `~pulp.plugin.ContentUnit` objects
        """
        raise NotImplementedError()
