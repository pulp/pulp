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
  exit_on_failed
  popd
}

tito_tag()
{
  # $1=<git-root>
  pushd $1
  $TITO tag $TITO_TAG_FLAGS && $GIT push origin HEAD && $GIT push --tags
  exit_on_failed
  popd
}

git_tag()
{
  # $1=<git-root>
  pushd $1
  $GIT tag -m "Build Tag" $BUILD_TAG && $GIT push --tags
  exit_on_failed
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
      exit_on_failed
      $GIT checkout $PARENT && $GIT pull --rebase
      exit_on_failed
      git_pre_tag_merge
      $GIT checkout $BRANCH
      exit_on_failed
    else
      $GIT checkout $BRANCH && $GIT pull --rebase
      exit_on_failed
    fi
    popd
  done
}

git_pre_tag_merge()
{
  not_merged=(`$GIT branch --no-merged $PARENT | cut -c3-80`)
  case "${not_merged[@]}" in
    $BRANCH)
      echo "(pre-tag) Merging $BRANCH => $PARENT"
      echo ""
      $GIT log ..$BRANCH
      exit_on_failed
      echo ""
      read -p "Continue [y|n]: " ANS
      if [ $ANS = "y" ]
      then
        MESSAGE="Merge $BRANCH => $PARENT, pre-build"
        $GIT merge -m "$MESSAGE" $BRANCH
        exit_on_failed
        $GIT push origin HEAD
        exit_on_failed
      else
        exit 0
      fi
      ;;
    *)
      # skip, not our branch
      ;;
  esac
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
    exit_on_failed
    MESSAGE="Merge (-s ours) $BRANCH => $PARENT, post-build"
    $GIT merge -s ours -m "$MESSAGE" $BRANCH
    exit_on_failed
    $GIT push origin HEAD
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
    $GIT tag -l $BRANCH | grep $BRANCH >& /dev/null
    if [ $? = 0 ]; then
      echo "[$BRANCH] must be a branch."
      exit 1
    fi
    popd
  done
}

verify_version()
{
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

# verify the version
verify_version

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

