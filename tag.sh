#!/bin/bash
#
# Tagging script
#

VERSION=
TITO_TAG_FLAGS=
BUILD_TAG=
TAG="git tag"
PUSH="git push"
TITO_TAG="tito tag"
TAG_FLAGS="-m \"Correlated Build\""
PUSH_TAGS="git push --tags"

GIT_ROOTS="pulp pulp_rpm pulp_puppet"
PACKAGES="
  pulp/platform/
  pulp/builtins/
  pulp/products/pulp-rpm-product/
  pulp_rpm/
  pulp_puppet/"

FIND_VERSION_SCRIPT=\
$(cat << END
from tito import common as tito
tag = tito.get_latest_tagged_version('pulp')
version = tag.split('-')[0]
next_version = tito.increase_version(version)
print next_version
END
)

set_version()
{
  pushd pulp
  VERSION=`python -c "$FIND_VERSION_SCRIPT"`
  popd
}

tito_tag()
{
  pushd $1
  $TITO_TAG $TITO_TAG_FLAGS && $PUSH && $PUSH_TAGS
  popd
}

git_tag()
{
  pushd $1
  $TAG $TAG_FLAGS $BUILD_TAG && $PUSH_TAGS
  popd
}

usage()
{
cat << EOF
usage: $0 options

This script tags all pulp projects

OPTIONS:
   -h      Show this message
   -v      The pulp version (eg: 0.0.332)
   -a      Auto accept the changelog
EOF
}

while getopts "hav:" OPTION
do
  case $OPTION in
    h)
      usage
      exit 1
      ;;
    v)
      VERSION=$OPTARG
      ;;
    a)
      TITO_TAG_FLAGS="$TITO_TAG_FLAGS --accept-auto-changelog"
      ;;
    ?)
      usage
      exit
      ;;
  esac
done

# version based on main pulp project
# unless specified using -v
if [[ -z $VERSION ]]
then
  set_version
  if [ $? != 0 ]; then
    exit
  fi
fi

# confirmation
echo "Using:"
echo "  version [$VERSION]"
echo "  tito options [$TITO_TAG_FLAGS]"
echo ""
read -p "Continue [y|n]: " ANS
if [ $ANS != "y" ]
then
  exit 0
fi

# used by tagger
TITO_FORCED_VERSION=VERSION
export TITO_FORCED_VERSION

BUILD_TAG="build-$VERSION"

# tito tagging
for PACKAGE in $PACKAGES
do
  tito_tag $PACKAGE
  if [ $? != 0 ]; then
    exit
  fi
done

# git (correlated build) tagging
for GIT_ROOT in $GIT_ROOTS
do
  git_tag $GIT_ROOT
  if [ $? != 0 ]; then
    exit
  fi
done

