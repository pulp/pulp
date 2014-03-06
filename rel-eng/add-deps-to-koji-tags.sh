#!/usr/bin/env bash

if [[ $# < 2 ]] ; then
    echo "This script goes through all the rpm packages that pulp requires and adds them to "
    echo "a given koji tag. "

    echo 'Usage: add-packages-to-koji-tag <owner> <pulp-version> <release-stream>.  The release stream is optional.'
    echo "for example.  'add-deps-to-koji-tags.sh bcourt 2.4 testing' or 'add-deps-to-koji-tags.sh foo 2.4'"
    exit 1
fi

OWNER=$1
PULP_VERSION=$2
RELEASE_STREAM=$3

WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../)"
TITO_DIR="${WORKSPACE}/tito"
rm -Rf ${TITO_DIR}
mkdir -p ${TITO_DIR}

# If we use the stream
if [ ${RELEASE_STREAM} ]
then
    RELEASE_STREAM="-${RELEASE_STREAM}"
fi

PROJECTS="gofer python-okaara python-isodate"
PROJECTS_NON_RHEL5="m2crypto mod_wsgi createrepo"
PROJECTS_NON_RHEL5=("${PROJECTS_NON_RHEL5[@]} python-nectar python-semantic-version")
PROJECTS_NON_RHEL5=("${PROJECTS_NON_RHEL5[@]} python-celery python-amqp python-anyjson")
PROJECTS_NON_RHEL5=("${PROJECTS_NON_RHEL5[@]} python-celery python-amqp python-anyjson")
PROJECTS_NON_RHEL5=("${PROJECTS_NON_RHEL5[@]} python-billiard python-kombu python-requests")

PLATFORMS=("el5" "el6" "fc19" "fc20")
KOJI_PLATFORM_TAGS=("rhel5" "rhel6" "fedora19" "fedora20")

for ((i=0;i<${#PLATFORMS[@]};++i))
do
    platform=${PLATFORMS[i]}
    koji_platform=${KOJI_PLATFORM_TAGS[i]}
    koji_target="pulp-${PULP_VERSION}${RELEASE_STREAM}-${koji_platform}"
    projects=("${PROJECTS[@]}")
    if [ ${platform} != "el5" ]
    then
        projects="${PROJECTS[@]} ${PROJECTS_NON_RHEL5[@]}"
    fi
    for project in ${projects}
    do
        # Go get the current version from the spec file in the deps folder
        package_dir=`cat ${WORKSPACE}/pulp/rel-eng/packages/${project} | cut -f2 -d" "`
        package_dir="${WORKSPACE}/pulp/${package_dir}"
        spec=`ls ${package_dir}*.spec`
        version=`rpm --queryformat "%{RPMTAG_VERSION}-%{RPMTAG_RELEASE} " --specfile ${spec} | cut -f1 -d" "`
        version_without_dist="${version%.*}"
        # Qualified packaeg name with version and release
        package_nvr="${project}-${version_without_dist}.${platform}"

        # Check if the package (not including version has been added to the koji tag)
        koji list-pkgs --tag=${koji_target} --package=${project} &>/dev/null
        if [ $? != 0 ]
        then
            # add the package to the target
            echo "Add the package for ${project} to ${koji_target}"
            koji add-pkg ${koji_target} ${project} --owner=${OWNER}
        fi

        # Check if the package has been built in koji, We don't need to see the output, just need the
        # error code
        search_result=`koji search build ${package_nvr}`
        if [ ${search_result} ]
        then
            # The specific version of the package already exists in koji, lets add it to our target
            koji tag-pkg ${koji_target} ${package_nvr}
        else
            # The specific version of the package does not exist in koji.
            # Build the srpm with tito and then submit the rpm to koji
            pushd ${package_dir} &>/dev/null
            tito build --offline --srpm --output ${WORKSPACE}/tito --dist=.${platform}
            koji build ${koji_target} ${TITO_DIR}/${package_nvr}.src.rpm
            popd &>/dev/null
        fi
    done
done
