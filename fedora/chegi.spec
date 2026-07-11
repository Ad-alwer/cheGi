%global srcname chegi

Name:           python-%{srcname}
Version:        0.3.0
Release:        1%{?dist}
Summary:        The ultimate Git companion. Type less, do more.

License:        MIT
URL:            https://github.com/Ad-alwer/cheGi
Source0:        chegi-%{version}.tar.gz

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

%generate_buildrequires
%pyproject_buildrequires

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
* Sat Jul 11 2026 Ad-alwer <ad-alwer@github.com> - 0.3.0-1
- Initial COPR package
