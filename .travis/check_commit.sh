#!/bin/bash

# skip this check for everything but PRs
if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
  exit 0
fi

if [ "$TRAVIS_COMMIT_RANGE" != "" ]; then
  RANGE=$TRAVIS_COMMIT_RANGE
elif [ "$TRAVIS_COMMIT" != "" ]; then
  RANGE=$TRAVIS_COMMIT
fi

# Travis sends the ranges with 3 dots. Git only wants one.
if [[ "$RANGE" == *...* ]]; then
  RANGE=`echo $TRAVIS_COMMIT_RANGE | sed 's/\.\.\./../'`
else
  RANGE="$RANGE~..$RANGE"
fi

for sha in `git log --format=oneline --no-merges "$RANGE" | cut '-d ' -f1`
do
  python .travis/validate_commit_message.py $sha
  VALUE=$?

  if [ "$VALUE" -gt 0 ]; then
    exit $VALUE
  fi
done
