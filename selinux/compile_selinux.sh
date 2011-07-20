MODULE_NAME="pulp"
checkmodule -M -m -o ${MODULE_NAME}.mod ${MODULE_NAME}.te
semodule_package -o ${MODULE_NAME}.pp -m ${MODULE_NAME}.mod
