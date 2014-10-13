%global pkgname mongoengine
Name: python-mongoengine
Version: 0.7.10
Release: 2%{?dist}
Summary: A Python Document-Object Mapper for working with MongoDB

License: MIT
URL:     http://pypi.python.org/pypi/mongoengine/
Source0: http://pypi.python.org/packages/source/m/mongoengine/%{pkgname}-%{version}.tar.gz

Patch1: fix-requirements-pillow-instead-PIL.patch
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-dateutil

# python-sphinx is really old in epel6, use the compat package instead
%if 0%{?rhel} == 6
BuildRequires: python-sphinx10
%else
BuildRequires: python-sphinx
%endif

%if 0%{?fedora} >= 18
BuildRequires: python-pymongo
BuildRequires: python-django
BuildRequires: python-pymongo-gridfs
Requires: python-pymongo
Requires: python-pymongo-gridfs
%else
BuildRequires: python-pymongo
BuildRequires: Django
BuildRequires: python-pymongo-gridfs
Requires: python-pymongo >= 2.1.1
Requires: python-pymongo-gridfs
%endif

BuildRequires: mongodb-server
BuildRequires: python-blinker
%if 0%{?fedora} >= 19
BuildRequires: python-pillow
Requires:      python-pillow
%else
Requires: python-imaging
BuildRequires: python-imaging
%endif
BuildRequires: python-coverage
BuildRequires: python-nose
Requires: python-blinker


%description
MongoEngine is a Document-Object Mapper (think ORM,
but for document databases) for working with MongoDB
from Python. It uses a simple declarative API, similar
to the Django ORM.


%prep
%setup -q -n %{pkgname}-%{version}

%if 0%{?fedora} >= 19
%patch1 -p1
%endif

rm -rf mongoengine.egg-info


%build
python setup.py build

# python-sphinx10 has a different binary name for sphinx-build
# set the makefile's variable for the binary when needed
%if 0%{?rhel} == 6
PYTHONPATH=$(pwd) make -C docs html SPHINXBUILD='sphinx-1.0-build'
%else
PYTHONPATH=$(pwd) make -C docs html
%endif

#PYTHONPATH=$(pwd) make -C docs html
rm -f docs/_build/html/.buildinfo


%install
python setup.py install --skip-build --root %{buildroot}


%check
# Pass


%files
%doc README.rst LICENSE docs/_build/html
%{python_sitelib}/%{pkgname}
%{python_sitelib}/%{pkgname}-*.egg-info


%changelog
* Mon Oct 13 2014 Chris Duryee <cduryee@redhat.com> 0.7.10-2
- new package built with tito

* Tue Oct 08 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.10-2
- Fix BR
* Fri Sep 13 2013 Tim Flink <tflink@fedoraproject.org> - 0.7.10-1
- adding conditional dep and makefile change for epel6 sphinx
- updating to 0.7.10

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.9-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Mar 13 2013 Eduardo Echeverria  <echevemaster@gmail.com> - 0.7.9-5
- Fix setup.py (add python-pillow instead python-imaging)

* Mon Jan 28 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-4
- Add Requires: pymongo, python-gridfs for f17
- Add Requires: python-pymongo, python-pymongo-gridfs for f18+
- Add Requires: python-blinker, python-imaging

* Sun Jan 27 2013 Yohan Graterol <yohangraterol92@gamil.com> - 0.7.9-3
- Built and included test
- Add BuildRequires: python-django >= 1.3

* Sun Jan 27 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-2
- Built and included sphinx docs
- Add BuildRequires: python-sphinx, python-pymongo, pymongo-gridfs
- Add BuildRequires: python-coverage, python-nose

* Thu Jan 17 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-1
- Initial packaging
