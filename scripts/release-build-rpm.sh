export TMP_RPM_DIR=.tmp-rpm
git clone https://github.com/noironetworks/3rdparty-rpm.git ${TMP_RPM_DIR}
mv ${TMP_RPM_DIR}/acitoolkit/rpm .
rm -rf ${TMP_RPM_DIR}

BUILD_DIR=$WORKSPACE/rpmbuild RELEASE=$BUILD_NUMBER ./rpm/build-rpm.sh
