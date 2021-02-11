!define PRODUCT_NAME "Nicotine+"
!define PRODUCT_VERSION "3.0.0"
!define PRODUCT_PUBLISHER "Nicotine+ Team"
!define PRODUCT_WEB_SITE "https://nicotine-plus.org"
!define PRODUCT_DIR_REGKEY "Software\Nicotine+"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

!include "MUI.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE_3LINES
!define MUI_ICON "nicotine.ico"
!define MUI_UNICON "nicotine.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\COPYING"
; Validate installation directory
!define MUI_DIRECTORYPAGE_VERIFYONLEAVE
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Name "${PRODUCT_NAME} (${PRODUCT_VERSION})"
BrandingText "${PRODUCT_NAME}"
OutFile "${PRODUCT_NAME}-${PRODUCT_VERSION}.exe"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
ManifestDPIAware true

; Installer

Function .onInit
  ${IfNot} ${AtLeastWin7}
    MessageBox MB_OK|MB_ICONEXCLAMATION "Nicotine+ requires Windows 7 or later."
    Quit
  ${EndIf}

  ${If} ${ARCH} == "i686"
    StrCpy $InstDir "$PROGRAMFILES\Nicotine+"
  ${Else}
    StrCpy $InstDir "$PROGRAMFILES64\Nicotine+"
  ${EndIf}
FunctionEnd

Section -Pre
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"

  ${If} $R0 != ""        
    DetailPrint "Removing previous installation."
    ExecWait '$R0 /S _?=$INSTDIR'
  ${EndIf}
SectionEnd

Section "Core" Core
  SectionIn RO
  SetOverwrite on
  SetOutPath "$INSTDIR"
  File /r "..\..\dist\Nicotine+\"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  CreateShortCut "$SMPROGRAMS\Nicotine+.lnk" "$INSTDIR\Nicotine+.exe"
  CreateShortCut "$DESKTOP\Nicotine+.lnk" "$INSTDIR\Nicotine+.exe"
SectionEnd

; Uninstaller

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer." /SD IDOK
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" /SD IDYES IDYES +2
  Abort
FunctionEnd

Section Uninstall
  Delete "$INSTDIR\uninst.exe"
  Delete "$SMPROGRAMS\Nicotine+.lnk"
  Delete "$DESKTOP\Nicotine+.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd
