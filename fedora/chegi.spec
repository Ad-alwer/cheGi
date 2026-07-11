%global srcname chegi

%if 0%{?fedora} >= 45
# questionary not yet packaged for Python 3.15 on rawhide
# bundled as Source1 and installed from local file in %%prep
%global __requires_exclude ^python3-questionary$
%endif

Name:           python-%{srcname}
Version:        0.3.0
Release:        3%{?dist}
Summary:        The ultimate Git companion. Type less, do more.

License:        MIT
URL:            https://github.com/Ad-alwer/cheGi
Source0:        chegi-%{version}.tar.gz
%if 0%{?fedora} >= 45
Source1:        https://files.pythonhosted.org/packages/source/q/questionary/questionary-2.1.1.tar.gz
%endif

BuildArch:      noarch

BuildRequires:  python3-devel >= 3.9
BuildRequires:  pyproject-rpm-macros

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
%if 0%{?fedora} >= 45
pip install --no-index %{SOURCE1}
%endif

%generate_buildrequires
%pyproject_buildrequires -N

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l %{srcname}

%check
%pyproject_check_import

%files -n python3-%{srcname} -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/chegi

%changelog
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-3
- Bundle questionary as Source1 for Fedora 45+ (rawhide) where system
  python3-questionary requires python(abi) 3.14 (unavailable on F45)
- Install questionary from local source file in %%prep (no network needed)
- Revert to %%pyproject_buildrequires -N and exclude auto-generated BR
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-2
- Install questionary via pip on Fedora 45+ (rawhide) to handle Python 3.15
  incompatibility
- Use %%pyproject_buildrequires -N to skip auto-generated runtime BuildRequires
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-1
- Initial COPR package
