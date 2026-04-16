import os
import shutil
import zipfile
import subprocess
from builder.config import APP_NAME, RELEASES_DIR, DIST_DIR, AUTHOR_NAME
from builder.utils import build_base_binary

def build_all_windows(version):
    build_base_binary()
    exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    
    # 1. Portable .zip
    zip_name = f"{APP_NAME}_{version}_windows_amd64.zip"
    zip_path = os.path.join(RELEASES_DIR, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(exe_path, arcname=f"{APP_NAME}.exe")
    print(f"Created {zip_name}")

    # 2. MSI Installer (Requires WiX Toolset)
    # Using the defined AUTHOR_NAME as the Manufacturer
    wxs_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
        <Product Id="*" Name="{APP_NAME}" Language="1033" Version="{version}" Manufacturer="{AUTHOR_NAME}" UpgradeCode="12345678-1234-1234-1234-123456789012">
            <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />
            <MediaTemplate EmbedCab="yes" />
            <Feature Id="ProductFeature" Title="{APP_NAME}" Level="1">
                <ComponentGroupRef Id="ProductComponents" />
            </Feature>
        </Product>
        <Fragment>
            <Directory Id="TARGETDIR" Name="SourceDir">
                <Directory Id="ProgramFilesFolder">
                    <Directory Id="INSTALLFOLDER" Name="{APP_NAME}" />
                </Directory>
            </Directory>
        </Fragment>
        <Fragment>
            <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
                <Component Id="MainExecutable" Guid="*">
                    <File Id="ChegiEXE" Source="{exe_path}" KeyPath="yes" />
                </Component>
            </ComponentGroup>
        </Fragment>
    </Wix>
    """
    
    wxs_path = os.path.join(DIST_DIR, f"{APP_NAME}.wxs")
    wixobj_path = os.path.join(DIST_DIR, f"{APP_NAME}.wixobj")
    msi_path = os.path.join(RELEASES_DIR, f"{APP_NAME}_{version}_windows_amd64.msi")

    with open(wxs_path, "w") as f:
        f.write(wxs_content)

    try:
        # candle compiles XML to wixobj, light links wixobj to msi
        subprocess.run(["candle", "-ext", "WixUIExtension", wxs_path, "-out", wixobj_path], check=True)
        subprocess.run(["light", "-ext", "WixUIExtension", wixobj_path, "-out", msi_path], check=True)
        print(f"Created MSI installer: {msi_path}")
    except FileNotFoundError:
        print("WiX toolset (candle/light) not found. Skipping MSI creation. (This will run fine on GitHub Actions).")
