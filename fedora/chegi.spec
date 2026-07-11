%global srcname chegi

%if 0%{?fedora} >= 45
# questionary not yet packaged for Python 3.15 on rawhide
# exclude auto-generated Requires to allow install without system package
# users can pip install questionary on rawhide until Fedora catches up
%global __requires_exclude ^python3-questionary$
%endif

Name:           python-%{srcname}
Version:        0.3.0
Release:        4%{?dist}
Summary:        The ultimate Git companion. Type less, do more.

License:        MIT
URL:            https://github.com/Ad-alwer/cheGi
Source0:        chegi-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel >= 3.9
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-pip

%description
cheGi is a Git companion that makes common Git operations faster and
easier. Type less, do more.

%package -n python3-%{srcname}
Summary:        %{summary}

%description -n python3-%{srcname}
cheGi is a Git companion that makes common Git operations faster and
easier. Type less, do more.

%prep
%autosetup -n cheGi-%{version}

%generate_buildrequires
%pyproject_buildrequires -N

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l %{srcname}

%check
%if 0%{?fedora} < 45
%pyproject_check_import
%endif

%files -n python3-%{srcname} -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/chegi

%changelog
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-4
- Simplify rawhide fix: use %%pyproject_buildrequires -N, exclude auto
  Requires on F45+, accept that questionary RPM not available on rawhide
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-3
- Bundle questionary as Source1 for Fedora 45+ (rawhide) where system
  python3-questionary requires python(abi) 3.14 (unavailable on F45)
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-2
- Install questionary via pip on Fedora 45+ (rawhide) to handle Python 3.15
  incompatibility
- Use %%pyproject_buildrequires -N to skip auto-generated runtime BuildRequires
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-1
- Initial COPR package
