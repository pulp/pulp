DATE=`date`
ERRATUM_ID=DEMO_ID_`python -c "import time; print int(time.time())"`
ERRATUM_TITLE="Demo Errata created on ${DATE}"
ERRATUM_DESCRIPTION="This is a multi line description\n of the erratum.\n"
ERRATUM_VERSION=1
ERRATUM_RELEASE=1
ERRATUM_TYPE="enhancement"
ERRATUM_STATUS="final"
ERRATUM_UPDATED="${DATE}"
ERRATUM_ISSUED="${DATE}"
ERRATUM_REF_CSV="references.csv"
ERRATUM_PKG_CSV="package_list.csv_NON_EXISTENT_FILE"
ERRATUM_FROM="pulp-list@redhat.com"
ERRATUM_PUSHCOUNT=1
ERRATUM_SEVERITY="example severity"
ERRATUM_RIGHTS="example rights"
ERRATUM_SUMMARY="example summary"
ERRATUM_SOLUTIONS="example solutions"

pulp-admin repo uploads errata --repo-id errata_demo --erratum-id "${ERRATUM_ID}" --title "${ERRATUM_TITLE}" --description "${ERRATUM_DESCRIPTION}" \
    --version "${ERRATUM_VERSION}" --release "${ERRATUM_RELEASE}" --type "${ERRATUM_TYPE}" --status "${ERRATUM_STATUS}" --updated "${ERRATUM_UPDATED}" \
    --issued "${ERRATUM_UPDATED}" --reference-csv "${ERRATUM_REF_CSV}" --pkglist-csv "${ERRATUM_PKG_CSV}" --from "${ERRATUM_FROM}" --pushcount "${ERRATUM_PUSHCOUNT}" \
    --severity "${ERRATUM_SEVERITY}" --rights "${ERRATUM_RIGHTS}" --summary "${ERRATUM_SUMMARY}" --solution "${ERRATUM_SOLUTION}" 
