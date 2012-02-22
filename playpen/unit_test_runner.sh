#
# Harness for repeatedly running Pulp unit tests and reporting on the
# results. This was originally developed to help debug issues with our
# RHEL jenkins slaves.
#
# Before using be sure to review the variables at the top and change
# as necessary for your system.
#

REPORT_DIR="/var/www/html/pulp"

REPORT_TMP="$REPORT_DIR/tmp.txt"
SUMMARY="$REPORT_DIR/summary.txt"
WWW_SUMMARY="$REPORT_DIR/tests.txt"
WWW_REPORT="$REPORT_DIR/report.txt"

SUCCESSES=0
SUCCESSES_STORE="$REPORT_DIR/.successes"
FAILURES=0
FAILURES_STORE="$REPORT_DIR/.failures"

COMMAND="nosetests ./test/unit"

HOST_PREFIX="http://localhost/pulp"

for i in {1..5}
do

  # Report headers
  echo "= Pulp RHEL Unit Test Summary =" > $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY
  echo `cat /etc/issue` >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY
  echo "Running Test #$[i+1]" >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY

  # Run the tests
  $COMMAND &> $REPORT_TMP

  if [ "$?" -ne "0" ]
  then
    FAILURES=$[FAILURES+1]
    echo $FAILURES > $FAILURES_STORE
    timestamp=`date +%B-%d-%H-%M`
    report_filename="$REPORT_DIR/failure-$i-$timestamp.txt"
    cp $REPORT_TMP $report_filename
  else
    SUCCESSES=$[SUCCESSES+1]
    echo $SUCCESSES > $SUCCESSES_STORE
  fi

  # Report summary information
  echo "Successes: $SUCCESSES" > $SUMMARY
  echo "Failures:  $FAILURES" >> $SUMMARY

  echo "Successes: $SUCCESSES" >> $WWW_SUMMARY
  echo "Failures:  $FAILURES" >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY

  # Output the latest run
  echo "== Latest Run ==" >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY
  cat $REPORT_TMP >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY

  # Generate links to failures
  echo "== Failed Runs ==" >> $WWW_SUMMARY
  echo "(most recent first; insert filename into the URL)" >> $WWW_SUMMARY
  echo "" >> $WWW_SUMMARY
  for f in `ls -tr $REPORT_DIR/failure-*`
  do
    filename=`basename $f`
    echo "$HOST_PREFIX/$filename" >> $WWW_SUMMARY
  done
  echo "" >> $WWW_SUMMARY

  # Once the report is finished, overwrite the report
  cp $WWW_SUMMARY $WWW_REPORT

done

