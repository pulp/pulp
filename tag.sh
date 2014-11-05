#!/bin/bash
#
# Tagging script
#

set -e  # exit on failed

VERSION=
BUILD_TAG=
GIT="git"
TITO="tito"
TITO_TAG_FLAGS=
BRANCH=
PARENT='master'

GIT_ROOTS="pulp pulp_rpm pulp_puppet"
PACKAGES="
  pulp/
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
  popd
}

tito_tag()
{
  # $1=<git-root>
  pushd $1
  $TITO tag $TITO_TAG_FLAGS && $GIT push origin HEAD && $GIT push --tags
  popd
}

git_tag()
{
  # $1=<git-root>
  pushd $1
  $GIT tag -m "Build Tag" $BUILD_TAG && $GIT push --tags
  popd
}

git_prep()
{
  verify_branch
  for DIR in $GIT_ROOTS
  do
    pushd $DIR
    echo "Preparing git in repository [$DIR] using [$BRANCH]"
    if [ "$PARENT" != "$BRANCH" ]
    then
      $GIT checkout $BRANCH && $GIT pull --rebase
      $GIT checkout $PARENT && $GIT pull --rebase
      git_pre_tag_merge
      $GIT checkout $BRANCH
    else
      $GIT checkout $BRANCH && $GIT pull --rebase
    fi
    popd
  done
}

git_pre_tag_merge()
{
  commits=(`$GIT log $PARENT..$BRANCH`)
  if [ ${#commits[@]} -gt 0 ]
  then
    echo "(pre-tag) Merging $BRANCH => $PARENT"
    echo ""
    $GIT log $PARENT..$BRANCH
    echo ""
    read -p "Continue [y|n]: " ANS
    if [ $ANS = "y" ]
    then
      MESSAGE="Merge $BRANCH => $PARENT, pre-build"
      $GIT merge -m "$MESSAGE" $BRANCH
      $GIT push origin HEAD
    else
      exit 0
    fi
  fi
}

git_post_tag_merge()
{
  if [ "$PARENT" = "$BRANCH" ]
  then
    return
  fi
  for DIR in $GIT_ROOTS
  do
    echo "(post-tag) Merging (-s ours) $DIR $BRANCH => $PARENT"
    pushd $DIR
    $GIT checkout $PARENT
    $GIT log $PARENT..$BRANCH
    echo ""
    read -p "Continue [y|n]: " ANS
    if [ $ANS = "y" ]
    then
      MESSAGE="Merge (-s ours) $BRANCH => $PARENT, post-build"
      $GIT merge -s ours -m "$MESSAGE" $BRANCH
      $GIT push origin HEAD
    fi
    popd
  done
}

verify_branch()
{
  for DIR in $GIT_ROOTS
  do
    pushd $DIR
    $GIT fetch --tags
    set +e
    $GIT tag -l $BRANCH | grep $BRANCH >& /dev/null
    if [ $? = 0 ]; then
      echo "[$BRANCH] must be a branch."
      exit 1
    fi
    set -e
    popd
  done
}

verify_version()
{
  set +e
  echo $VERSION | grep -E "(alpha|beta)$"
  if [ $? = 1 ]
  then
    echo ""
    echo "WARNING: [$VERSION] does not contain (alpha|beta)."
    read -p "Is this a STABLE build [y|n]: " ANS
    if [ $ANS != "y" ]
    then
      exit 0
    fi
  fi
  set -e
}

usage()
{
cat << EOF
usage: $0 options

This script tags all pulp projects

OPTIONS:
   -h      Show this message
   -v      The pulp version and release. Eg: 2.3.0-1
   -a      Auto accept the changelog
   -b      Checkout the specified branch
   -p      A parent branch. (default: master)
EOF
}

while getopts "hav:b:p:" OPTION
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
    p)
      PARENT=$OPTARG
      ;;
    ?)
      usage
      exit
      ;;
  esac
done

# git (pre-tag) preparation
if [[ -n $BRANCH ]]
then
  if [ "$BRANCH" = "$PARENT" ]
  then
    BRANCHES=$BRANCH
  else
    BRANCHES="$PARENT/$BRANCH"
  fi
  echo "Prepare git repositories using: [$BRANCHES]"
  read -p "Continue [y|n]: " ANS
  if [ $ANS = "y" ]
  then
    git_prep
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

# verify the version
verify_version

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

# git (post-tag) merging
if [[ -n $BRANCH ]]
then
  git_post_tag_merge
fi

