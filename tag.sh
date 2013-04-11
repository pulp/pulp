#!/bin/bash
#
# Tagging script
#

VERSION=
BUILD_TAG=
GIT="git"
TITO="tito"
TITO_TAG_FLAGS=
BRANCH=

GIT_ROOTS="pulp pulp_rpm pulp_puppet"
PACKAGES="
  pulp/platform/
  pulp/builtins/
  pulp/nodes/
  pulp_rpm/
  pulp_puppet/"

NEXT_VR_SCRIPT=\
$(cat << END
import sys
sys.path.insert(0, 'rel-eng/lib')
import tools
print tools.next()
END
)

set_version()
{
  pushd pulp
  VERSION=`python -c "$NEXT_VR_SCRIPT"`
  exit_on_failed
  popd
}

tito_tag()
{
  pushd $1
  $TITO tag $TITO_TAG_FLAGS && $GIT push origin HEAD && $GIT push --tags
  exit_on_failed
  popd
}

git_tag()
{
  pushd $1
  $GIT tag -m "Build Tag" $BUILD_TAG && $GIT push --tags
  exit_on_failed
  popd
}

git_prep()
{
  verify_branch $1
  for DIR in $GIT_ROOTS
  do
    pushd $DIR
    echo "Preparing git in repository: $DIR using: $1"
    $GIT checkout $1 && $GIT pull --rebase
    exit_on_failed
    popd
  done
}

verify_branch()
{
  for DIR in $GIT_ROOTS
  do
    pushd $DIR
    $GIT fetch --tags
    $GIT tag -l $1 | grep $1 >& /dev/null
    if [ $? = 0 ]; then
      echo "[$1] must be a branch."
      exit 1
    fi
    popd
  done
}

exit_on_failed()
{
  if [ $? != 0 ]; then
    exit 1
  fi
}

usage()
{
cat << EOF
usage: $0 options

This script tags all pulp projects

OPTIONS:
   -h      Show this message
   -v      The pulp version and release. Eg: 2.0.6-1
   -a      Auto accept the changelog
   -b      Checkout the specified branch
EOF
}

while getopts "hav:b:" OPTION
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
    b)
      BRANCH=$OPTARG
      ;;
    ?)
      usage
      exit
      ;;
  esac
done

# git preparation
if [[ -n $BRANCH ]]
then
  echo "Prepare git repositories using: [$BRANCH]"
  read -p "Continue [y|n]: " ANS
  if [ $ANS = "y" ]
  then
    git_prep $BRANCH
    echo ""
    echo ""
  fi
fi

# version based on main pulp project
# unless specified using -v
if [[ -z $VERSION ]]
then
  set_version
fi

# confirmation
echo ""
echo ""
echo "Using:"
echo "  version [$VERSION]"
echo "  tito options: $TITO_TAG_FLAGS"
echo ""
read -p "Continue [y|n]: " ANS
if [ $ANS != "y" ]
then
  exit 0
fi

# used by tagger
PULP_VERSION_AND_RELEASE=$VERSION
export PULP_VERSION_AND_RELEASE

BUILD_TAG="build-$VERSION"

# tito tagging
for PACKAGE in $PACKAGES
do
  tito_tag $PACKAGE
done

# git (correlated build) tagging
for GIT_ROOT in $GIT_ROOTS
do
  git_tag $GIT_ROOT
done

