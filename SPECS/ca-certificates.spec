%define pkidir %{_sysconfdir}/pki
%define catrustdir %{_sysconfdir}/pki/ca-trust
%define classic_tls_bundle ca-bundle.crt
%define openssl_format_trust_bundle ca-bundle.trust.crt
%define p11_format_bundle ca-bundle.trust.p11-kit
%define legacy_default_bundle ca-bundle.legacy.default.crt
%define legacy_disable_bundle ca-bundle.legacy.disable.crt
%define java_bundle java/cacerts

Summary: The Mozilla CA root certificate bundle
Name: ca-certificates

# For the package version number, we use: year.{upstream version}
#
# The {upstream version} can be found as symbol
# NSS_BUILTINS_LIBRARY_VERSION in file nss/lib/ckfw/builtins/nssckbi.h
# which corresponds to the data in file nss/lib/ckfw/builtins/certdata.txt.
#
# The files should be taken from a released version of NSS, as published
# at https://ftp.mozilla.org/pub/mozilla.org/security/nss/releases/
#
# The versions that are used by the latest released version of 
# Mozilla Firefox should be available from:
# https://hg.mozilla.org/releases/mozilla-release/raw-file/default/security/nss/lib/ckfw/builtins/nssckbi.h
# https://hg.mozilla.org/releases/mozilla-release/raw-file/default/security/nss/lib/ckfw/builtins/certdata.txt
#
# The most recent development versions of the files can be found at
# http://hg.mozilla.org/projects/nss/raw-file/default/lib/ckfw/builtins/nssckbi.h
# http://hg.mozilla.org/projects/nss/raw-file/default/lib/ckfw/builtins/certdata.txt
# (but these files might have not yet been released).
#
# (until 2012.87 the version was based on the cvs revision ID of certdata.txt,
# but in 2013 the NSS projected was migrated to HG. Old version 2012.87 is 
# equivalent to new version 2012.1.93, which would break the requirement 
# to have increasing version numbers. However, the new scheme will work, 
# because all future versions will start with 2013 or larger.)

Version: 2024.2.69_v8.0.303
# On RHEL 7.x, please keep the release version >= 70
# When rebasing on Y-Stream (7.y), use 71, 72, 73, ...
# When rebasing on Z-Stream (7.y.z), use 70.0, 70.1, 70.2, ...
Release: 73%{?dist}
License: Public Domain

Group: System Environment/Base
URL: http://www.mozilla.org/

#Please always update both certdata.txt and nssckbi.h
Source0: certdata.txt
Source1: nssckbi.h
Source2: update-ca-trust
Source3: trust-fixes
Source4: certdata2pem.py
Source5: ca-legacy.conf
Source6: ca-legacy
Source9: ca-legacy.8.txt
Source10: update-ca-trust.8.txt
Source11: README.usr
Source12: README.etc
Source13: README.extr
Source14: README.java
Source15: README.openssl
Source16: README.pem
Source17: README.src
Source18: README.ca-certificates

BuildArch: noarch

Requires: p11-kit >= 0.23.5
Requires: p11-kit-trust >= 0.23.5
BuildRequires: perl
BuildRequires: python
BuildRequires: openssl
BuildRequires: asciidoc
BuildRequires: libxslt

%description
This package contains the set of CA certificates chosen by the
Mozilla Foundation for use with the Internet PKI.

%prep
rm -rf %{name}
mkdir %{name}
mkdir %{name}/certs
mkdir %{name}/certs/legacy-default
mkdir %{name}/certs/legacy-disable
mkdir %{name}/java

%build
pushd %{name}/certs
 pwd
 cp %{SOURCE0} .
 python %{SOURCE4} >c2p.log 2>c2p.err
popd
pushd %{name}
 (
   cat <<EOF
# This is a bundle of X.509 certificates of public Certificate
# Authorities.  It was generated from the Mozilla root CA list.
# These certificates and trust/distrust attributes use the file format accepted
# by the p11-kit-trust module.
#
# Source: nss/lib/ckfw/builtins/certdata.txt
# Source: nss/lib/ckfw/builtins/nssckbi.h
#
# Generated from:
EOF
   cat %{SOURCE1}  |grep -w NSS_BUILTINS_LIBRARY_VERSION | awk '{print "# " $2 " " $3}';
   echo '#';
 ) > %{p11_format_bundle}

 touch %{legacy_default_bundle}
 NUM_LEGACY_DEFAULT=`find certs/legacy-default -type f | wc -l`
 if [ $NUM_LEGACY_DEFAULT -ne 0 ]; then
     for f in certs/legacy-default/*.crt; do 
       echo "processing $f"
       tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
       alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
       targs=""
       if [ -n "$tbits" ]; then
          for t in $tbits; do
             targs="${targs} -addtrust $t"
          done
       fi
       if [ -n "$targs" ]; then
          echo "legacy default flags $targs for $f" >> info.trust
          openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> %{legacy_default_bundle}
       fi
     done
 fi

 touch %{legacy_disable_bundle}
 NUM_LEGACY_DISABLE=`find certs/legacy-disable -type f | wc -l`
 if [ $NUM_LEGACY_DISABLE -ne 0 ]; then
     for f in certs/legacy-disable/*.crt; do 
       echo "processing $f"
       tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
       alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
       targs=""
       if [ -n "$tbits" ]; then
          for t in $tbits; do
             targs="${targs} -addtrust $t"
          done
       fi
       if [ -n "$targs" ]; then
          echo "legacy disable flags $targs for $f" >> info.trust
          openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> %{legacy_disable_bundle}
       fi
     done
 fi

 P11FILES=`find certs -name \*.tmp-p11-kit | wc -l`
 if [ $P11FILES -ne 0 ]; then
   for p in certs/*.tmp-p11-kit; do 
     cat "$p" >> %{p11_format_bundle}
   done
 fi
 # Append our trust fixes
 cat %{SOURCE3} >> %{p11_format_bundle}
popd

#manpage
cp %{SOURCE10} %{name}/update-ca-trust.8.txt
asciidoc.py -v -d manpage -b docbook %{name}/update-ca-trust.8.txt
xsltproc --nonet -o %{name}/update-ca-trust.8 /usr/share/asciidoc/docbook-xsl/manpage.xsl %{name}/update-ca-trust.8.xml

cp %{SOURCE9} %{name}/ca-legacy.8.txt
asciidoc.py -v -d manpage -b docbook %{name}/ca-legacy.8.txt
xsltproc --nonet -o %{name}/ca-legacy.8 /usr/share/asciidoc/docbook-xsl/manpage.xsl %{name}/ca-legacy.8.xml


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p -m 755 $RPM_BUILD_ROOT%{pkidir}/tls/certs
mkdir -p -m 755 $RPM_BUILD_ROOT%{pkidir}/java
mkdir -p -m 755 $RPM_BUILD_ROOT%{_sysconfdir}/ssl
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source/anchors
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/source/blacklist
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl
mkdir -p -m 755 $RPM_BUILD_ROOT%{catrustdir}/extracted/java
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/anchors
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/blacklist
mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy
mkdir -p -m 755 $RPM_BUILD_ROOT%{_bindir}
mkdir -p -m 755 $RPM_BUILD_ROOT%{_mandir}/man8

install -p -m 644 %{name}/update-ca-trust.8 $RPM_BUILD_ROOT%{_mandir}/man8
install -p -m 644 %{name}/ca-legacy.8 $RPM_BUILD_ROOT%{_mandir}/man8
install -p -m 644 %{SOURCE11} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/README
install -p -m 644 %{SOURCE12} $RPM_BUILD_ROOT%{catrustdir}/README
install -p -m 644 %{SOURCE13} $RPM_BUILD_ROOT%{catrustdir}/extracted/README
install -p -m 644 %{SOURCE14} $RPM_BUILD_ROOT%{catrustdir}/extracted/java/README
install -p -m 644 %{SOURCE15} $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/README
install -p -m 644 %{SOURCE16} $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/README
install -p -m 644 %{SOURCE17} $RPM_BUILD_ROOT%{catrustdir}/source/README

mkdir -p -m 755 $RPM_BUILD_ROOT%{_datadir}/doc/%{name}-%{version}
install -p -m 644 %{SOURCE18} $RPM_BUILD_ROOT%{_datadir}/doc/%{name}-%{version}/README

install -p -m 644 %{name}/%{p11_format_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

install -p -m 644 %{name}/%{legacy_default_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
install -p -m 644 %{name}/%{legacy_disable_bundle} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}

install -p -m 644 %{SOURCE5} $RPM_BUILD_ROOT%{catrustdir}/ca-legacy.conf

touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
touch -r %{SOURCE0} $RPM_BUILD_ROOT%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}

# TODO: consider to dynamically create the update-ca-trust script from within
#       this .spec file, in order to have the output file+directory names at once place only.
install -p -m 755 %{SOURCE2} $RPM_BUILD_ROOT%{_bindir}/update-ca-trust

install -p -m 755 %{SOURCE6} $RPM_BUILD_ROOT%{_bindir}/ca-legacy

# touch ghosted files that will be extracted dynamically
# Set chmod 444 to use identical permission
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/tls-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/tls-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/email-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/email-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/objsign-ca-bundle.pem
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/pem/objsign-ca-bundle.pem
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
touch $RPM_BUILD_ROOT%{catrustdir}/extracted/%{java_bundle}
chmod 444 $RPM_BUILD_ROOT%{catrustdir}/extracted/%{java_bundle}

# /etc/ssl/certs symlink for 3rd-party tools
sln ../pki/tls/certs \
    $RPM_BUILD_ROOT%{_sysconfdir}/ssl/certs
# legacy filenames
sln %{catrustdir}/extracted/pem/tls-ca-bundle.pem \
    $RPM_BUILD_ROOT%{pkidir}/tls/cert.pem
sln %{catrustdir}/extracted/pem/tls-ca-bundle.pem \
    $RPM_BUILD_ROOT%{pkidir}/tls/certs/%{classic_tls_bundle}
sln %{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle} \
    $RPM_BUILD_ROOT%{pkidir}/tls/certs/%{openssl_format_trust_bundle}
sln %{catrustdir}/extracted/%{java_bundle} \
    $RPM_BUILD_ROOT%{pkidir}/%{java_bundle}

%clean
rm -rf $RPM_BUILD_ROOT


%pre
if [ $1 -gt 1 ] ; then
  # Upgrade or Downgrade.
  # If the classic filename is a regular file, then we are upgrading
  # from an old package and we will move it to an .rpmsave backup file.
  # If the filename is a symbolic link, then we are good already.
  # If the system will later be downgraded to an old package with regular 
  # files, and afterwards updated again to a newer package with symlinks,
  # and the old .rpmsave backup file didn't get cleaned up,
  # then we don't backup again. We keep the older backup file.
  # In other words, if an .rpmsave file already exists, we don't overwrite it.
  #
  if ! test -e %{pkidir}/%{java_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/%{java_bundle}; then
      # a file exists
	  if ! test -L %{pkidir}/%{java_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/%{java_bundle} %{pkidir}/%{java_bundle}.rpmsave
      fi
    fi
  fi

  if ! test -e %{pkidir}/tls/certs/%{classic_tls_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/tls/certs/%{classic_tls_bundle}; then
      # a file exists
      if ! test -L %{pkidir}/tls/certs/%{classic_tls_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/tls/certs/%{classic_tls_bundle} %{pkidir}/tls/certs/%{classic_tls_bundle}.rpmsave
      fi
    fi
  fi

  if ! test -e %{pkidir}/tls/certs/%{openssl_format_trust_bundle}.rpmsave; then
    # no backup yet
    if test -e %{pkidir}/tls/certs/%{openssl_format_trust_bundle}; then
      # a file exists
      if ! test -L %{pkidir}/tls/certs/%{openssl_format_trust_bundle}; then
        # it's an old regular file, not a link
        mv -f %{pkidir}/tls/certs/%{openssl_format_trust_bundle} %{pkidir}/tls/certs/%{openssl_format_trust_bundle}.rpmsave
      fi
    fi
  fi
fi


%post
#if [ $1 -gt 1 ] ; then
#  # when upgrading or downgrading
#fi
%{_bindir}/ca-legacy install
%{_bindir}/update-ca-trust


%files
%defattr(-,root,root,-)

%dir %{_sysconfdir}/ssl
%dir %{pkidir}/tls
%dir %{pkidir}/tls/certs
%dir %{pkidir}/java
%dir %{catrustdir}
%dir %{catrustdir}/source
%dir %{catrustdir}/source/anchors
%dir %{catrustdir}/source/blacklist
%dir %{catrustdir}/extracted
%dir %{catrustdir}/extracted/pem
%dir %{catrustdir}/extracted/openssl
%dir %{catrustdir}/extracted/java
%dir %{_datadir}/pki
%dir %{_datadir}/pki/ca-trust-source
%dir %{_datadir}/pki/ca-trust-source/anchors
%dir %{_datadir}/pki/ca-trust-source/blacklist
%dir %{_datadir}/pki/ca-trust-legacy

%config(noreplace) %{catrustdir}/ca-legacy.conf

%{_mandir}/man8/update-ca-trust.8.gz
%{_mandir}/man8/ca-legacy.8.gz
%{_datadir}/pki/ca-trust-source/README
%{catrustdir}/README
%{catrustdir}/extracted/README
%{catrustdir}/extracted/java/README
%{catrustdir}/extracted/openssl/README
%{catrustdir}/extracted/pem/README
%{catrustdir}/source/README
%{_datadir}/doc/%{name}-%{version}/README

# symlinks for old locations
%{pkidir}/tls/cert.pem
%{pkidir}/tls/certs/%{classic_tls_bundle}
%{pkidir}/tls/certs/%{openssl_format_trust_bundle}
%{pkidir}/%{java_bundle}
# symlink directory
%{_sysconfdir}/ssl/certs

# master bundle file with trust
%{_datadir}/pki/ca-trust-source/%{p11_format_bundle}

%{_datadir}/pki/ca-trust-legacy/%{legacy_default_bundle}
%{_datadir}/pki/ca-trust-legacy/%{legacy_disable_bundle}
# update/extract tool
%{_bindir}/update-ca-trust
%{_bindir}/ca-legacy
%ghost %{catrustdir}/source/ca-bundle.legacy.crt
# files extracted files
%ghost %{catrustdir}/extracted/pem/tls-ca-bundle.pem
%ghost %{catrustdir}/extracted/pem/email-ca-bundle.pem
%ghost %{catrustdir}/extracted/pem/objsign-ca-bundle.pem
%ghost %{catrustdir}/extracted/openssl/%{openssl_format_trust_bundle}
%ghost %{catrustdir}/extracted/%{java_bundle}


%changelog
*Fri Nov 29 2024 Jonathan Dieter - 2024.2.69_v8.0.303-73
- Update to CKBI 2.69_v8.0.303 from NSS 3.101.1 - Fixes CVE-2023-37920

*Wed Sep 06 2023 Robert Relyea <rrelyea@redhat.com> - 2023.2.60_v7.0.306-72
- hand merge the two 'GlobalSign ECC Root CA R4' certs together and the two 'AC RAIZ FNMT-RCM' certs together to keep p11kit from getting confused.

*Tue Aug 01 2023 Robert Relyea <rrelyea@redhat.com> - 2023.2.60_v7.0.306-71
- Update to CKBI 2.60_v7.0.306 from NSS 3.91
-    Removing:
-     # Certificate "Camerfirma Global Chambersign Root"
-     # Certificate "Staat der Nederlanden EV Root CA"
-     # Certificate "OpenTrust Root CA G1"
-     # Certificate "Swedish Government Root Authority v1"
-     # Certificate "DigiNotar Root CA G2"
-     # Certificate "Federal Common Policy CA"
-     # Certificate "TC TrustCenter Universal CA III"
-     # Certificate "CCA India 2007"
-     # Certificate "ipsCA Global CA Root"
-     # Certificate "ipsCA Main CA Root"
-     # Certificate "Macao Post eSignTrust Root Certification Authority"
-     # Certificate "InfoNotary CSP Root"
-     # Certificate "DigiNotar Root CA"
-     # Certificate "Root CA"
-     # Certificate "GPKIRootCA"
-     # Certificate "D-TRUST Qualified Root CA 1 2007:PN"
-     # Certificate "TC TrustCenter Universal CA I"
-     # Certificate "TC TrustCenter Universal CA II"
-     # Certificate "TC TrustCenter Class 2 CA II"
-     # Certificate "TC TrustCenter Class 4 CA II"
-     # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı"
-     # Certificate "CertRSA01"
-     # Certificate "KISA RootCA 3"
-     # Certificate "A-CERT ADVANCED"
-     # Certificate "A-Trust-Qual-01"
-     # Certificate "A-Trust-nQual-01"
-     # Certificate "Serasa Certificate Authority II"
-     # Certificate "TDC Internet"
-     # Certificate "America Online Root Certification Authority 2"
-     # Certificate "RSA Security Inc"
-     # Certificate "Public Notary Root"
-     # Certificate "Autoridade Certificadora Raiz Brasileira"
-     # Certificate "Post.Trust Root CA"
-     # Certificate "Entrust.net Secure Server Certification Authority"
-     # Certificate "ePKI EV SSL Certification Authority - G1"
-    Adding:
-     # Certificate "DigiCert TLS ECC P384 Root G5"
-     # Certificate "DigiCert TLS RSA4096 Root G5"
-     # Certificate "DigiCert SMIME ECC P384 Root G5"
-     # Certificate "DigiCert SMIME RSA4096 Root G5"
-     # Certificate "Certainly Root R1"
-     # Certificate "Certainly Root E1"
-     # Certificate "E-Tugra Global Root CA RSA v3"
-     # Certificate "E-Tugra Global Root CA ECC v3"
-     # Certificate "DIGITALSIGN GLOBAL ROOT RSA CA"
-     # Certificate "DIGITALSIGN GLOBAL ROOT ECDSA CA"
-     # Certificate "BJCA Global Root CA1"
-     # Certificate "BJCA Global Root CA2"
-     # Certificate "Symantec Enterprise Mobile Root for Microsoft"
-     # Certificate "A-Trust-Root-05"
-     # Certificate "ADOCA02"
-     # Certificate "StartCom Certification Authority G2"
-     # Certificate "ATHEX Root CA"
-     # Certificate "EBG Elektronik Sertifika Hizmet Sağlayıcısı"
-     # Certificate "GeoTrust Primary Certification Authority"
-     # Certificate "thawte Primary Root CA"
-     # Certificate "VeriSign Class 3 Public Primary Certification Authority - G5"
-     # Certificate "America Online Root Certification Authority 1"
-     # Certificate "Juur-SK"
-     # Certificate "ComSign CA"
-     # Certificate "ComSign Secured CA"
-     # Certificate "ComSign Advanced Security CA"
-     # Certificate "Global Chambersign Root"
-     # Certificate "Sonera Class2 CA"
-     # Certificate "VeriSign Class 3 Public Primary Certification Authority - G3"
-     # Certificate "VeriSign, Inc."
-     # Certificate "GTE CyberTrust Global Root"
-     # Certificate "Equifax Secure Global eBusiness CA-1"
-     # Certificate "Equifax"
-     # Certificate "Class 1 Primary CA"
-     # Certificate "Swiss Government Root CA III"
-     # Certificate "Application CA G4 Root"
-     # Certificate "SSC GDL CA Root A"
-     # Certificate "GlobalSign Code Signing Root E45"
-     # Certificate "GlobalSign Code Signing Root R45"
-     # Certificate "Entrust Code Signing Root Certification Authority - CSBR1"

*Thu Jul 28 2022 Bob Relyea <rrelyea@redhat.com> - 2022.2.54-74
- Update to CKBI 2.54 from NSS 3.79
-    Removing:
-     # Certificate "TrustCor ECA-1"
-     # Certificate "TrustCor RootCert CA-2"
-     # Certificate "TrustCor RootCert CA-1"
-     # Certificate "Network Solutions Certificate Authority"
-     # Certificate "COMODO Certification Authority"
-     # Certificate "Autoridad de Certificacion Raiz del Estado Venezolano"
-     # Certificate "Microsec e-Szigno Root CA 2009"
-     # Certificate "TWCA Root Certification Authority"
-     # Certificate "Izenpe.com"
-     # Certificate "state-institutions"
-     # Certificate "GlobalSign"
-     # Certificate "Common Policy"
-     # Certificate "A-Trust-nQual-03"
-     # Certificate "A-Trust-Qual-02"
-     # Certificate "Autoridad de Certificacion Firmaprofesional CIF A62634068"
-     # Certificate "Government Root Certification Authority"
-     # Certificate "AC Raíz Certicámara S.A."

*Wed Jul 27 2022 Bob Relyea <rrelyea@redhat.com> - 2022.2.54-73
- Update to CKBI 2.54 from NSS 3.79

*Fri Jul 15 2022 Bob Relyea <rrelyea@redhat.com> - 2022.2.54-72
- Update to CKBI 2.54 from NSS 3.79
-    Adding:
-     # Certificate "CAEDICOM Root"
-     # Certificate "I.CA Root CA/RSA"
-     # Certificate "MULTICERT Root Certification Authority 01"
-     # Certificate "Certification Authority of WoSign G2"
-     # Certificate "CA WoSign ECC Root"
-     # Certificate "CCA India 2015 SPL"
-     # Certificate "Swedish Government Root Authority v3"
-     # Certificate "Swedish Government Root Authority v2"
-     # Certificate "Tunisian Root Certificate Authority - TunRootCA2"
-     # Certificate "OpenTrust Root CA G1"
-     # Certificate "OpenTrust Root CA G2"
-     # Certificate "OpenTrust Root CA G3"
-     # Certificate "Certplus Root CA G1"
-     # Certificate "Certplus Root CA G2"
-     # Certificate "Government Root Certification Authority"
-     # Certificate "A-Trust-Qual-02"
-     # Certificate "Thailand National Root Certification Authority - G1"
-     # Certificate "TrustCor ECA-1"
-     # Certificate "TrustCor RootCert CA-2"
-     # Certificate "TrustCor RootCert CA-1"
-     # Certificate "Certification Authority of WoSign"
-     # Certificate "CA 沃通根证书"
-     # Certificate "SSC GDL CA Root B"
-     # Certificate "SAPO Class 2 Root CA"
-     # Certificate "SAPO Class 3 Root CA"
-     # Certificate "SAPO Class 4 Root CA"
-     # Certificate "CA Disig Root R1"
-     # Certificate "Autoridad Certificadora Raíz Nacional de Uruguay"
-     # Certificate "ApplicationCA2 Root"
-     # Certificate "GlobalSign"
-     # Certificate "Symantec Class 3 Public Primary Certification Authority - G6"
-     # Certificate "Symantec Class 3 Public Primary Certification Authority - G4"
-     # Certificate "Halcom Root CA"
-     # Certificate "Swisscom Root EV CA 2"
-     # Certificate "CFCA GT CA"
-     # Certificate "Digidentity L3 Root CA - G2"
-     # Certificate "SITHS Root CA v1"
-     # Certificate "Macao Post eSignTrust Root Certification Authority (G02)"
-     # Certificate "Autoridade Certificadora Raiz Brasileira v2"
-     # Certificate "Swisscom Root CA 2"
-     # Certificate "IGC/A AC racine Etat francais"
-     # Certificate "PersonalID Trustworthy RootCA 2011"
-     # Certificate "Swedish Government Root Authority v1"
-     # Certificate "Swiss Government Root CA II"
-     # Certificate "Swiss Government Root CA I"
-     # Certificate "Network Solutions Certificate Authority"
-     # Certificate "COMODO Certification Authority"
-     # Certificate "LuxTrust Global Root"
-     # Certificate "AC1 RAIZ MTIN"
-     # Certificate "Microsoft Root Certificate Authority 2011"
-     # Certificate "CCA India 2011"
-     # Certificate "ANCERT Certificados Notariales V2"
-     # Certificate "ANCERT Certificados CGN V2"
-     # Certificate "EE Certification Centre Root CA"
-     # Certificate "DigiNotar Root CA G2"
-     # Certificate "Federal Common Policy CA"
-     # Certificate "Autoridad de Certificacion Raiz del Estado Venezolano"
-     # Certificate "Autoridad de Certificacion Raiz del Estado Venezolano"
-     # Certificate "China Internet Network Information Center EV Certificates Root"
-     # Certificate "Verizon Global Root CA"
-     # Certificate "SwissSign Silver Root CA - G3"
-     # Certificate "SwissSign Platinum Root CA - G3"
-     # Certificate "SwissSign Gold Root CA - G3"
-     # Certificate "Microsec e-Szigno Root CA 2009"
-     # Certificate "SITHS CA v3"
-     # Certificate "Certinomis - Autorité Racine"
-     # Certificate "ANF Server CA"
-     # Certificate "Thawte Premium Server CA"
-     # Certificate "Thawte Server CA"
-     # Certificate "TC TrustCenter Universal CA III"
-     # Certificate "KEYNECTIS ROOT CA"
-     # Certificate "I.CA - Standard Certification Authority, 09/2009"
-     # Certificate "I.CA - Qualified Certification Authority, 09/2009"
-     # Certificate "VI Registru Centras RCSC (RootCA)"
-     # Certificate "CCA India 2007"
-     # Certificate "Autoridade Certificadora Raiz Brasileira v1"
-     # Certificate "ipsCA Global CA Root"
-     # Certificate "ipsCA Main CA Root"
-     # Certificate "Actalis Authentication CA G1"
-     # Certificate "A-Trust-Qual-03"
-     # Certificate "AddTrust External CA Root"
-     # Certificate "ECRaizEstado"
-     # Certificate "Configuration"
-     # Certificate "FNMT-RCM"
-     # Certificate "StartCom Certification Authority"
-     # Certificate "TWCA Root Certification Authority"
-     # Certificate "VeriSign Class 3 Public Primary Certification Authority - G4"
-     # Certificate "thawte Primary Root CA - G2"
-     # Certificate "GeoTrust Primary Certification Authority - G2"
-     # Certificate "VeriSign Universal Root Certification Authority"
-     # Certificate "thawte Primary Root CA - G3"
-     # Certificate "GeoTrust Primary Certification Authority - G3"
-     # Certificate "E-ME SSI (RCA)"
-     # Certificate "ACEDICOM Root"
-     # Certificate "Autoridad Certificadora Raiz de la Secretaria de Economia"
-     # Certificate "Correo Uruguayo - Root CA"
-     # Certificate "CNNIC ROOT"
-     # Certificate "Common Policy"
-     # Certificate "Macao Post eSignTrust Root Certification Authority"
-     # Certificate "Staat der Nederlanden Root CA - G2"
-     # Certificate "NetLock Platina (Class Platinum) Főtanúsítvány"
-     # Certificate "AC Raíz Certicámara S.A."
-     # Certificate "Cisco Root CA 2048"
-     # Certificate "CA Disig"
-     # Certificate "InfoNotary CSP Root"
-     # Certificate "UCA Global Root"
-     # Certificate "UCA Root"
-     # Certificate "DigiNotar Root CA"
-     # Certificate "Starfield Services Root Certificate Authority"
-     # Certificate "I.CA - Qualified root certificate"
-     # Certificate "I.CA - Standard root certificate"
-     # Certificate "e-Guven Kok Elektronik Sertifika Hizmet Saglayicisi"
-     # Certificate "Japanese Government"
-     # Certificate "AdminCA-CD-T01"
-     # Certificate "Admin-Root-CA"
-     # Certificate "Izenpe.com"
-     # Certificate "TÜBİTAK UEKAE Kök Sertifika Hizmet Sağlayıcısı - Sürüm 3"
-     # Certificate "Halcom CA FO"
-     # Certificate "Halcom CA PO 2"
-     # Certificate "Root CA"
-     # Certificate "GPKIRootCA"
-     # Certificate "ACNLB"
-     # Certificate "state-institutions"
-     # Certificate "state-institutions"
-     # Certificate "SECOM Trust Systems CO.,LTD."
-     # Certificate "D-TRUST Qualified Root CA 1 2007:PN"
-     # Certificate "D-TRUST Root Class 2 CA 2007"
-     # Certificate "D-TRUST Root Class 3 CA 2007"
-     # Certificate "SSC Root CA A"
-     # Certificate "SSC Root CA B"
-     # Certificate "SSC Root CA C"
-     # Certificate "Autoridad de Certificacion de la Abogacia"
-     # Certificate "Root CA Generalitat Valenciana"
-     # Certificate "VAS Latvijas Pasts SSI(RCA)"
-     # Certificate "ANCERT Certificados CGN"
-     # Certificate "ANCERT Certificados Notariales"
-     # Certificate "ANCERT Corporaciones de Derecho Publico"
-     # Certificate "GLOBALTRUST"
-     # Certificate "Certipost E-Trust TOP Root CA"
-     # Certificate "Certipost E-Trust Primary Qualified CA"
-     # Certificate "Certipost E-Trust Primary Normalised CA"
-     # Certificate "Cybertrust Global Root"
-     # Certificate "GlobalSign"
-     # Certificate "IGC/A"
-     # Certificate "S-TRUST Authentication and Encryption Root CA 2005:PN"
-     # Certificate "TC TrustCenter Universal CA I"
-     # Certificate "TC TrustCenter Universal CA II"
-     # Certificate "TC TrustCenter Class 2 CA II"
-     # Certificate "TC TrustCenter Class 4 CA II"
-     # Certificate "Swisscom Root CA 1"
-     # Certificate "Microsec e-Szigno Root CA"
-     # Certificate "LGPKI"
-     # Certificate "AC RAIZ DNIE"
-     # Certificate "Common Policy"
-     # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı"
-     # Certificate "A-Trust-nQual-03"
-     # Certificate "A-Trust-nQual-03"
-     # Certificate "CertRSA01"
-     # Certificate "KISA RootCA 1"
-     # Certificate "KISA RootCA 3"
-     # Certificate "NetLock Minositett Kozjegyzoi (Class QA) Tanusitvanykiado"
-     # Certificate "A-CERT ADVANCED"
-     # Certificate "A-Trust-Qual-01"
-     # Certificate "A-Trust-nQual-01"
-     # Certificate "A-Trust-Qual-02"
-     # Certificate "Staat der Nederlanden Root CA"
-     # Certificate "Serasa Certificate Authority II"
-     # Certificate "TDC Internet"
-     # Certificate "America Online Root Certification Authority 2"
-     # Certificate "Autoridad de Certificacion Firmaprofesional CIF A62634068"
-     # Certificate "Government Root Certification Authority"
-     # Certificate "RSA Security Inc"
-     # Certificate "Public Notary Root"
-     # Certificate "GeoTrust Global CA"
-     # Certificate "GeoTrust Global CA 2"
-     # Certificate "GeoTrust Universal CA"
-     # Certificate "GeoTrust Universal CA 2"
-     # Certificate "QuoVadis Root Certification Authority"
-     # Certificate "Autoridade Certificadora Raiz Brasileira"
-     # Certificate "Post.Trust Root CA"
-     # Certificate "Microsoft Root Authority"
-     # Certificate "Microsoft Root Certificate Authority"
-     # Certificate "Microsoft Root Certificate Authority 2010"
-     # Certificate "Entrust.net Secure Server Certification Authority"
-     # Certificate "UTN-USERFirst-Object"
-     # Certificate "BYTE Root Certification Authority 001"
-     # Certificate "CISRCA1"
-     # Certificate "ePKI Root Certification Authority - G2"
-     # Certificate "ePKI EV SSL Certification Authority - G1"
-     # Certificate "AC Raíz Certicámara S.A."
-     # Certificate "SSL.com EV Root Certification Authority RSA"
-     # Certificate "LuxTrust Global Root 2"
-     # Certificate "ACA ROOT"
-     # Certificate "Security Communication ECC RootCA1"
-     # Certificate "Security Communication RootCA3"
-     # Certificate "CHAMBERS OF COMMERCE ROOT - 2016"
-     # Certificate "Network Solutions RSA Certificate Authority"
-     # Certificate "Network Solutions ECC Certificate Authority"
-     # Certificate "Australian Defence Public Root CA"
-     # Certificate "SI-TRUST Root"
-     # Certificate "Halcom Root Certificate Authority"
-     # Certificate "Application CA G3 Root"
-     # Certificate "GLOBALTRUST 2015"
-     # Certificate "Microsoft ECC Product Root Certificate Authority 2018"
-     # Certificate "emSign Root CA - G2"
-     # Certificate "emSign Root CA - C2"
-     # Certificate "Microsoft ECC TS Root Certificate Authority 2018"
-     # Certificate "DigiCert CS ECC P384 Root G5"
-     # Certificate "DigiCert CS RSA4096 Root G5"
-     # Certificate "DigiCert RSA4096 Root G5"
-     # Certificate "DigiCert ECC P384 Root G5"
-     # Certificate "HARICA Code Signing RSA Root CA 2021"
-     # Certificate "HARICA Code Signing ECC Root CA 2021"
-     # Certificate "Microsoft Identity Verification Root Certificate Authority 2020"

*Mon Jul 11 2022 Bob Relyea <rrelyea@redhat.com> - 2022.2.54-71
- Update to CKBI 2.54 from NSS 3.79
-    Removing:
-     # Certificate "GlobalSign Root CA - R2"
-     # Certificate "Cybertrust Global Root"
-     # Certificate "Explicitly Distrusted DigiNotar PKIoverheid G2"
-    Adding:
-     # Certificate "TunTrust Root CA"
-     # Certificate "HARICA TLS RSA Root CA 2021"
-     # Certificate "HARICA TLS ECC Root CA 2021"
-     # Certificate "HARICA Client RSA Root CA 2021"
-     # Certificate "HARICA Client ECC Root CA 2021"
-     # Certificate "Autoridad de Certificacion Firmaprofesional CIF A62634068"
-     # Certificate "vTrus ECC Root CA"
-     # Certificate "vTrus Root CA"
-     # Certificate "ISRG Root X2"
-     # Certificate "HiPKI Root CA - G1"
-     # Certificate "Telia Root CA v2"
-     # Certificate "D-TRUST BR Root CA 1 2020"
-     # Certificate "D-TRUST EV Root CA 1 2020"

*Tue Sep 14 2021 Bob Relyea <rrelyea@redhat.com> - 2021.2.50-72
- Fix expired certificate.
-    Removing:
-     # Certificate "DST Root CA X3"

*Wed Jun 16 2021 Bob Relyea <rrelyea@redhat.com> - 2021.2.50-71
- Update to CKBI 2.50 from NSS 3.67
   - version number update only

*Fri Jun 11 2021 Bob Relyea <rrelyea@redhat.com> - 2021.2.48-71
- Update to CKBI 2.48 from NSS 3.66
-    Removing:
-     # Certificate "Verisign Class 3 Public Primary Certification Authority - G3"
-     # Certificate "GeoTrust Global CA"
-     # Certificate "GeoTrust Universal CA"
-     # Certificate "GeoTrust Universal CA 2"
-     # Certificate "QuoVadis Root CA"
-     # Certificate "Sonera Class 2 Root CA"
-     # Certificate "Taiwan GRCA"
-     # Certificate "GeoTrust Primary Certification Authority"
-     # Certificate "thawte Primary Root CA"
-     # Certificate "VeriSign Class 3 Public Primary Certification Authority - G5"
-     # Certificate "GeoTrust Primary Certification Authority - G3"
-     # Certificate "thawte Primary Root CA - G2"
-     # Certificate "thawte Primary Root CA - G3"
-     # Certificate "GeoTrust Primary Certification Authority - G2"
-     # Certificate "VeriSign Universal Root Certification Authority"
-     # Certificate "VeriSign Class 3 Public Primary Certification Authority - G4"
-     # Certificate "Trustis FPS Root CA"
-     # Certificate "EE Certification Centre Root CA"
-     # Certificate "LuxTrust Global Root 2"
-     # Certificate "Symantec Class 1 Public Primary Certification Authority - G4"
-     # Certificate "Symantec Class 2 Public Primary Certification Authority - G4"
-    Adding:
-     # Certificate "Microsoft ECC Root Certificate Authority 2017"
-     # Certificate "Microsoft RSA Root Certificate Authority 2017"
-     # Certificate "e-Szigno Root CA 2017"
-     # Certificate "certSIGN Root CA G2"
-     # Certificate "Trustwave Global Certification Authority"
-     # Certificate "Trustwave Global ECC P256 Certification Authority"
-     # Certificate "Trustwave Global ECC P384 Certification Authority"
-     # Certificate "NAVER Global Root Certification Authority"
-     # Certificate "AC RAIZ FNMT-RCM SERVIDORES SEGUROS"
-     # Certificate "GlobalSign Secure Mail Root R45"
-     # Certificate "GlobalSign Secure Mail Root E45"
-     # Certificate "GlobalSign Root R46"
-     # Certificate "GlobalSign Root E46"
-     # Certificate "GLOBALTRUST 2020"
-     # Certificate "ANF Secure Server Root CA"
-     # Certificate "Certum EC-384 CA"
-     # Certificate "Certum Trusted Root CA"

*Tue Jun 09 2020 Bob Relyea <rrelyea@redhat.com> - 2020.2.41-79
- Update to CKBI 2.41 from NSS 3.53.0
-    Removing:
-     # Certificate "AddTrust Low-Value Services Root"
-     # Certificate "AddTrust External Root"
-     # Certificate "UTN USERFirst Email Root CA"
-     # Certificate "Certplus Class 2 Primary CA"
-     # Certificate "Deutsche Telekom Root CA 2"
-     # Certificate "Staat der Nederlanden Root CA - G2"
-     # Certificate "Swisscom Root CA 2"
-     # Certificate "Certinomis - Root CA"
-    Adding:
-     # Certificate "Entrust Root Certification Authority - G4"
- fix permissions on ghosted files.

*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-76
- Update to CKBI 2.32 from NSS 3.44
-   Removing:
-   # Certificate "Visa eCommerce Root"
-   # Certificate "AC Raiz Certicamara S.A."
-   # Certificate "TC TrustCenter Class 3 CA II"
-   # Certificate "ComSign CA"
-   # Certificate "S-TRUST Universal Root CA"
-   # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
-   # Certificate "Certplus Root CA G1"
-   # Certificate "Certplus Root CA G2"
-   # Certificate "OpenTrust Root CA G1"
-   # Certificate "OpenTrust Root CA G2"
-   # Certificate "OpenTrust Root CA G3"
-  Adding:
-   # Certificate "GlobalSign Root CA - R6"
-   # Certificate "OISTE WISeKey Global Root GC CA"
-   # Certificate "GTS Root R1"
-   # Certificate "GTS Root R2"
-   # Certificate "GTS Root R3"
-   # Certificate "GTS Root R4"
-   # Certificate "UCA Global G2 Root"
-   # Certificate "UCA Extended Validation Root"
-   # Certificate "Certigna Root CA"
-   # Certificate "emSign Root CA - G1"
-   # Certificate "emSign ECC Root CA - G3"
-   # Certificate "emSign Root CA - C1"
-   # Certificate "emSign ECC Root CA - C3"
-   # Certificate "Hongkong Post Root CA 3"

* Wed Mar 14 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-70.0
- Update to CKBI 2.22 from NSS 3.35

* Wed Nov 29 2017 Kai Engert <kaie@redhat.com> - 2017.2.20-71
- Update to CKBI 2.20 from NSS 3.34.1

* Thu Oct 26 2017 Kai Engert <kaie@redhat.com> - 2017.2.18-71
- Update to CKBI 2.18 (pre-release snapshot)

* Tue Sep 26 2017 Kai Engert <kaie@redhat.com> - 2017.2.16-71
- Update to CKBI 2.16 from NSS 3.32. In addition to removals/additions,
  Mozilla removed code signing trust from all CAs (rhbz#1472933)

* Fri Apr 28 2017 Kai Engert <kaie@redhat.com> - 2017.2.14-71
- Update to CKBI 2.14 from NSS 3.30.2

* Fri Mar 10 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-73
- No longer trust legacy CAs

* Fri Mar 10 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-72
- Changed the packaged bundle to use the flexible p11-kit-object-v1 file format,
  as a preparation to fix bugs in the interaction between p11-kit-trust and
  Mozilla applications, such as Firefox, Thunderbird etc.
- For CAs trusted by Mozilla, set attribute nss-mozilla-ca-policy: true
- Require p11-kit 0.23.5
- Added an utility to help with comparing output of the trust dump command.

* Tue Jan 17 2017 Kai Engert <kaie@redhat.com> - 2017.2.11-71
- Update to CKBI 2.11 from NSS 3.28.1 with legacy modifications.
- Use comments in extracted bundle files.
- Change packaging script to support empty legacy bundles.

* Tue May 10 2016 Kai Engert <kaie@redhat.com> - 2016.2.6-73
- Use sln, not ln, to avoid the dependency on coreutils (rhbz#1328586)

* Mon Apr 25 2016 Kai Engert <kaie@redhat.com> - 2015.2.6-72
- Fixed a typo in a manual page (rhbz#1303960)

* Wed Jan 27 2016 Kai Engert <kaie@redhat.com> - 2015.2.6-71
- Update to CKBI 2.6 from NSS 3.21 with legacy modifications.

* Thu Apr 23 2015 Kai Engert <kaie@redhat.com> - 2015.2.4-71
- Update to CKBI 2.4 from NSS 3.18.1 with legacy modifications.

* Tue Apr 14 2015 Kai Engert <kaie@redhat.com> - 2015.2.3-72
- Fix a typo in the ca-legacy manual page (rhbz#1208850)

* Tue Mar 31 2015 Kai Engert <kaie@redhat.com> - 2015.2.3-71
- Update to CKBI 2.3 from NSS 3.18 with legacy modifications.
- Add an alternative version of the "Thawte Premium Server CA" root,
  which carries a SHA1-RSA signature, to allow OpenJDK to verify applets
  which contain that version of the root certificate.
  This change doesn't add trust for another key, because both versions
  of the certificate use the same public key (rhbz#1170982).
- Add a patch to the source RPM that documents the changes from the
  upstream version.
- Introduce the ca-legacy utility, a manual page, and the ca-legacy.conf
  configuration file.
- The new scriptlets require the coreutils package.
- Remove the obsolete blacklist.txt file.

* Wed Sep 17 2014 Stef Walter <stefw@redhat.com> - 2014.1.98-72
- The BasicConstraints fix for Entrust Root is no longer necessary.
  In addition it was invalid for p11-kit 0.20.x. rhbz#1130485

* Wed Sep 03 2014 Kai Engert <kaie@redhat.com> - 2014.1.98-71
- Update to CKBI 1.98 from NSS 3.16.1
- building on RHEL 7 no longer requires java-openjdk
- added more detailed instructions for release numbers on RHEL branches,
  to avoid problems when rebasing on both z- and y-stream branches.

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 2013.1.95-71
- Mass rebuild 2013-12-27

* Tue Dec 17 2013 Kai Engert <kaie@redhat.com> - 2013.1.95-70.1
- Update to CKBI 1.95 from NSS 3.15.3.1

* Fri Oct 18 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-70.1
- Only create backup files if there is an original file, rhbz#999017

* Tue Sep 03 2013 Kai Engert <kaie@redhat.com> - 2013.1.94-70.0
- Update to CKBI 1.94 from NSS 3.15

* Wed Jul 17 2013 Kai Engert <kaie@redhat.com> - 2012.87-70.1
- improve manpage

* Tue Jul 09 2013 Kai Engert <kaie@redhat.com> - 2012.87-70.0
- use a release version that 's larger than on rhel 6

* Tue Jul 09 2013 Kai Engert <kaie@redhat.com> - 2012.87-10.4
- clarification updates to manual page

* Mon Jul 08 2013 Kai Engert <kaie@redhat.com> - 2012.87-10.3
- added a manual page and related build requirements
- simplify the README files now that we have a manual page
- set a certificate alias in trusted bundle (thanks to Ludwig Nussel)

* Mon May 27 2013 Kai Engert <kaie@redhat.com> - 2012.87-10.2
- use correct command in README files, rhbz#961809

* Mon Apr 22 2013 Kai Engert <kaie@redhat.com> - 2012.87-10.1
- Add myself as contributor to certdata2.pem.py and remove use of rcs/ident.
  (thanks to Michael Shuler for suggesting to do so)
- Update source URLs and comments, add source file for version information.

* Wed Mar 27 2013 Kai Engert <kaie@redhat.com> - 2012.87-10.0
- Use both label and serial to identify cert during conversion, rhbz#927601 

* Tue Mar 19 2013 Kai Engert <kaie@redhat.com> - 2012.87-9.fc19.1
- adjust to changed and new functionality provided by p11-kit 0.17.3
- updated READMEs to describe the new directory-specific treatment of files
- ship a new file that contains certificates with neutral trust
- ship a new file that contains distrust objects, and also staple a 
  basic constraint extension to one legacy root contained in the
  Mozilla CA list
- adjust the build script to dynamically produce most of above files
- add and own the anchors and blacklist subdirectories
- file generate-cacerts.pl is no longer required

* Fri Mar 08 2013 Kai Engert <kaie@redhat.com> - 2012.87-9
- Major rework for the Fedora SharedSystemCertificates feature.
- Only ship a PEM bundle file using the BEGIN TRUSTED CERTIFICATE file format.
- Require the p11-kit package that contains tools to automatically create
  other file format bundles.
- Convert old file locations to symbolic links that point to dynamically
  generated files.
- Old files, which might have been locally modified, will be saved in backup 
  files with .rpmsave extension.
- Added a update-ca-certificates script which can be used to regenerate
  the merged trusted output.
- Refer to the various README files that have been added for more detailed
  explanation of the new system.
- No longer require rsc for building.
- Add explanation for the future version numbering scheme,
  because the old numbering scheme was based on upstream using cvs,
  which is no longer true, and therefore can no longer be used.
- Includes changes from rhbz#873369.

* Thu Mar 07 2013 Kai Engert <kaie@redhat.com> - 2012.87-2.fc19.1
- Ship trust bundle file in /usr/share/pki/ca-trust-source/, temporarily in addition.
  This location will soon become the only place containing this file.

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2012.87-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Jan 04 2013 Paul Wouters <pwouters@redhat.com> - 2012.87-1
- Updated to r1.87 to blacklist mis-issued turktrust CA certs

* Wed Oct 24 2012 Paul Wouters <pwouters@redhat.com> - 2012.86-2
- Updated blacklist with 20 entries (Diginotar, Trustwave, Comodo(?)
- Fix to certdata2pem.py to also check for CKT_NSS_NOT_TRUSTED 

* Tue Oct 23 2012 Paul Wouters <pwouters@redhat.com> - 2012.86-1
- update to r1.86

* Mon Jul 23 2012 Joe Orton <jorton@redhat.com> - 2012.85-2
- add openssl to BuildRequires

* Mon Jul 23 2012 Joe Orton <jorton@redhat.com> - 2012.85-1
- update to r1.85

* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2012.81-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Feb 13 2012 Joe Orton <jorton@redhat.com> - 2012.81-1
- update to r1.81

* Thu Jan 12 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2011.80-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Nov  9 2011 Joe Orton <jorton@redhat.com> - 2011.80-1
- update to r1.80
- fix handling of certs with dublicate Subject names (#733032)

* Thu Sep  1 2011 Joe Orton <jorton@redhat.com> - 2011.78-1
- update to r1.78, removing trust from DigiNotar root (#734679)

* Wed Aug  3 2011 Joe Orton <jorton@redhat.com> - 2011.75-1
- update to r1.75

* Wed Apr 20 2011 Joe Orton <jorton@redhat.com> - 2011.74-1
- update to r1.74

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2011.70-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Wed Jan 12 2011 Joe Orton <jorton@redhat.com> - 2011.70-1
- update to r1.70

* Tue Nov  9 2010 Joe Orton <jorton@redhat.com> - 2010.65-3
- update to r1.65

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-3
- package /etc/ssl/certs symlink for third-party apps (#572725)

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-2
- rebuild

* Wed Apr  7 2010 Joe Orton <jorton@redhat.com> - 2010.63-1
- update to certdata.txt r1.63
- use upstream RCS version in Version

* Fri Mar 19 2010 Joe Orton <jorton@redhat.com> - 2010-4
- fix ca-bundle.crt (#575111)

* Thu Mar 18 2010 Joe Orton <jorton@redhat.com> - 2010-3
- update to certdata.txt r1.58
- add /etc/pki/tls/certs/ca-bundle.trust.crt using 'TRUSTED CERTICATE' format
- exclude ECC certs from the Java cacerts database
- catch keytool failures
- fail parsing certdata.txt on finding untrusted but not blacklisted cert

* Fri Jan 15 2010 Joe Orton <jorton@redhat.com> - 2010-2
- fix Java cacert database generation: use Subject rather than Issuer
  for alias name; add diagnostics; fix some alias names.

* Mon Jan 11 2010 Joe Orton <jorton@redhat.com> - 2010-1
- adopt Python certdata.txt parsing script from Debian

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2009-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jul 22 2009 Joe Orton <jorton@redhat.com> 2009-1
- update to certdata.txt r1.53

* Mon Feb 23 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2008-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Tue Oct 14 2008 Joe Orton <jorton@redhat.com> 2008-7
- update to certdata.txt r1.49

* Wed Jun 25 2008 Thomas Fitzsimmons <fitzsim@redhat.com> - 2008-6
- Change generate-cacerts.pl to produce pretty aliases.

* Mon Jun  2 2008 Joe Orton <jorton@redhat.com> 2008-5
- include /etc/pki/tls/cert.pem symlink to ca-bundle.crt

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-4
- use package name for temp dir, recreate it in prep

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-3
- fix source script perms
- mark packaged files as config(noreplace)

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-2
- add (but don't use) mkcabundle.pl
- tweak description
- use /usr/bin/keytool directly; BR java-openjdk

* Tue May 27 2008 Joe Orton <jorton@redhat.com> 2008-1
- Initial build (#448497)
