#!/usr/bin/env bash

if [[ $# < 3 ]] ; then
    echo "This script goes through all the rpm packages that pulp requires and adds them to "
    echo "a given koji tag. "

    echo 'Usage: add-packages-to-koji-tag <owner> <pulp-version> <release-stream>.  The release stream is must '
    echo 'be one of testing, beta or stable.'
    echo "For example.  'add-deps-to-koji-tags.sh bcourt 2.4 testing' or 'add-deps-to-koji-tags.sh foo 2.4 stable'"
    exit 1
fi

OWNER=$1
PULP_VERSION=$2
RELEASE_STREAM=$3

# Verify the release stream attribute and ensure that it is formatted properly for the rest of the script
if [ ${RELEASE_STREAM} == 'testing' ] ||  [ ${RELEASE_STREAM} == 'beta' ] || [ ${RELEASE_STREAM} == 'stable' ]
then
    if [ ${RELEASE_STREAM} != 'stable' ]
    then
        RELEASE_STREAM="-${RELEASE_STREAM}"
    else
        RELEASE_STREAM=""
    fi
else
    echo 'Error: Release stream must be one of testing, beta or stable'
    exit 1
fi

WORKSPACE="$(readlink -f $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../../)"
TITO_DIR="${WORKSPACE}/tito"
rm -Rf ${TITO_DIR}
mkdir -p ${TITO_DIR}


PROJECTS="gofer python-okaara python-isodate"
PROJECTS_NON_RHEL5="m2crypto mod_wsgi createrepo"
PROJECTS_NON_RHEL5=("${PROJECTS_NON_RHEL5[@]} python-nectar python-semantic-version")
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
        # Qualified package name with version and release
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
        echo "Searching koji for ${package_nvr}"
        search_result=`koji search build ${package_nvr}`
        if [ ${search_result} ]
        then
            koji list-tagged --latest ${koji_target}  | grep ${package_nvr}
            if [ $? != 0 ]
            then
                # The specific version of the package already exists in koji but has not been
                # tagged to our package.  Let's add it to the target
                echo "Found ${package_nvr} in koji already.  Adding to to ${koji_target}"
                koji tag-pkg ${koji_target} ${package_nvr}
            else
                echo "The pacakge ${package_nvr} is already a part of the tag ${koji_target}"
            fi
        else
            # The specific version of the package does not exist in koji.
            # Build the srpm with tito and then submit the rpm to koji
            echo "Building dependency srpm with koji: ${package_nvr}"
            pushd ${package_dir} &>/dev/null
            tito build --offline --srpm --output ${WORKSPACE}/tito --dist=.${platform}
            koji build ${koji_target} ${TITO_DIR}/${package_nvr}.src.rpm
            popd &>/dev/null
        fi
    done
done
