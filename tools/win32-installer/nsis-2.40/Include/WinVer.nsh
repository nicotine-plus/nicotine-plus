; ---------------------
;      WinVer.nsh
; ---------------------
;
; LogicLib extensions for handling Windows versions and service packs.
;
; IsNT checks if the installer is running on Windows NT family (NT4, 2000, XP, etc.)
;
;   ${If} ${IsNT}
;     DetailPrint "Running on NT. Installing Unicode enabled application."
;   ${Else}
;     DetailPrint "Not running on NT. Installing ANSI application."
;   ${EndIf}
;
; AtLeastWin<version> checks if the installer is running on Windows version at least as specified.
; IsWin<version> checks if the installer is running on Windows version exactly as specified.
; AtMostWin<version> checks if the installer is running on Windows version at most as specified.
;
; <version> can be replaced with the following values:
;
;   95
;   98
;   ME
;
;   NT4
;   2000
;   XP
;   2003
;   Vista
;
; AtLeastServicePack checks if the installer is running on Windows service pack version at least as specified.
; IsServicePack checks if the installer is running on Windows service pack version exactly as specified.
; AtMostServicePack checks if the installer is running on Windows service version pack at most as specified.
;
; Usage examples:
;
;   ${If} ${IsNT}
;   DetailPrint "Running on NT family."
;   DetailPrint "Surely not running on 95, 98 or ME."
;   ${AndIf} ${AtLeastWinNT4}
;     DetailPrint "Running on NT4 or better. Could even be 2003."
;   ${EndIf}
;
;   ${If} ${AtLeastWinXP}
;     DetailPrint "Running on XP or better."
;   ${EndIf}
;
;   ${If} ${IsWin2000}
;     DetailPrint "Running on 2000."
;   ${EndIf}
;
;   ${If} ${IsWin2000}
;   ${AndIf} ${AtLeastServicePack} 3
;   ${OrIf} ${AtLeastWinXP}
;     DetailPrint "Running Win2000 SP3 or above"
;   ${EndIf}
;
;   ${If} ${AtMostWinXP}
;     DetailPrint "Running on XP or older. Surely not running on Vista. Maybe 98, or even 95."
;   ${EndIf}
;
; Warning:
;
;   Windows 95 and NT both use the same version number. To avoid getting NT4 misidentified
;   as Windows 95 and vice-versa or 98 as a version higher than NT4, always use IsNT to
;   check if running on the NT family.
;
;     ${If} ${AtLeastWin95}
;     ${And} ${AtMostWinME}
;       DetailPrint "Running 95, 98 or ME."
;       DetailPrint "Actually, maybe it's NT4?"
;       ${If} ${IsNT}
;         DetailPrint "Yes, it's NT4! oops..."
;       ${Else}
;         DetailPrint "Nope, not NT4. phew..."
;       ${EndIf}
;     ${EndIf}

!verbose push
!verbose 3

!ifndef ___WINVER__NSH___
!define ___WINVER__NSH___

!include LogicLib.nsh

!define WINVER_95 0x400
!define WINVER_98 0x40A ;4.10
!define WINVER_ME 0x45A ;4.90

!define WINVER_NT4 0x400
!define WINVER_2000 0x500
!define WINVER_XP 0x501
!define WINVER_2003 0x502
!define WINVER_VISTA 0x600

!macro __GetWinVer
  !insertmacro _LOGICLIB_TEMP
  System::Call kernel32::GetVersion()i.s
  Pop $_LOGICLIB_TEMP
!macroend

!macro __ParseWinVer
  !insertmacro __GetWinVer
  Push $0
  IntOp $0 $_LOGICLIB_TEMP & 0xff
  IntOp $0 $0 << 8
  IntOp $_LOGICLIB_TEMP $_LOGICLIB_TEMP & 0xff00
  IntOp $_LOGICLIB_TEMP $_LOGICLIB_TEMP >> 8
  IntOp $_LOGICLIB_TEMP $_LOGICLIB_TEMP | $0
  Pop $0
!macroend

!macro _IsNT _a _b _t _f
  !insertmacro __GetWinVer
  IntOp $_LOGICLIB_TEMP $_LOGICLIB_TEMP & 0x80000000
  !insertmacro _== $_LOGICLIB_TEMP 0 `${_t}` `${_f}`
!macroend
!define IsNT `"" IsNT ""`

!macro __WinVer_DefineOSTest Test OS

  !define ${Test}Win${OS} `"" WinVer${Test} ${WINVER_${OS}}`

!macroend

!macro __WinVer_DefineOSTests Test

  !insertmacro __WinVer_DefineOSTest ${Test} 95
  !insertmacro __WinVer_DefineOSTest ${Test} 98
  !insertmacro __WinVer_DefineOSTest ${Test} ME
  !insertmacro __WinVer_DefineOSTest ${Test} NT4
  !insertmacro __WinVer_DefineOSTest ${Test} 2000
  !insertmacro __WinVer_DefineOSTest ${Test} XP
  !insertmacro __WinVer_DefineOSTest ${Test} 2003
  !insertmacro __WinVer_DefineOSTest ${Test} VISTA

!macroend

!macro _WinVerAtLeast _a _b _t _f
  !insertmacro __ParseWinVer
  !insertmacro _>= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend

!macro _WinVerIs _a _b _t _f
  !insertmacro __ParseWinVer
  !insertmacro _= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend

!macro _WinVerAtMost _a _b _t _f
  !insertmacro __ParseWinVer
  !insertmacro _<= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend

!insertmacro __WinVer_DefineOSTests AtLeast
!insertmacro __WinVer_DefineOSTests Is
!insertmacro __WinVer_DefineOSTests AtMost


!macro __GetWinServicePack
  !insertmacro _LOGICLIB_TEMP

  Push $0
  Push $1
  Push $2

  StrCpy $2 0

  ; $1 = malloc(sizeof(OSVERSIONINFOEXA))
  System::Alloc 156
  Pop $1
  StrCmp $1 0 Label_WinVer_ServicePack_End_${LOGICLIB_COUNTER}
    ; ($1)->dwOSVersionInfoSize = sizeof(OSVERSIONINFOEXA)
    System::Call /NOUNLOAD '*$1(&i4 156)'
    ; GetVersionEx($1)
    System::Call /NOUNLOAD 'kernel32::GetVersionEx(i r1) i.r0'
    StrCmp $0 0 Label_WinVer_ServicePack_GetVersion_${LOGICLIB_COUNTER}
      ; $2 = ($1)->wServicePackMajor
      System::Call /NOUNLOAD '*$1(&t148, &i2.r2)'
      Goto Label_WinVer_ServicePack_End_${LOGICLIB_COUNTER}

Label_WinVer_ServicePack_GetVersion_${LOGICLIB_COUNTER}:
      ; ($1)->dwOSVersionInfoSize = sizeof(OSVERSIONINFOA)
      System::Call /NOUNLOAD '*$1(&i4 148)'
      ; GetVersionEx($1)
      System::Call /NOUNLOAD 'kernel32::GetVersionEx(i r1) i.r0'
      StrCmp $0 0 Label_WinVer_ServicePack_End_${LOGICLIB_COUNTER}
        ; $2 = ($1)->szCSDVersion
        System::Call /NOUNLOAD '*$1(&t20, &t128.r2)'
        StrCpy $0 $2 13
        StrCmp $0 "Service Pack " 0 +3
          StrCpy $2 $2 "" 13
          Goto +2
        StrCpy $2 0

Label_WinVer_ServicePack_End_${LOGICLIB_COUNTER}:
    ; free($1)
    StrCmp $1 0 +2
      System::Free $1

  StrCpy $_LOGICLIB_TEMP $2

  Pop $2
  Pop $1
  Pop $0

  !insertmacro _IncreaseCounter

!macroend

!define AtLeastServicePack `"" AtLeastServicePack`
!macro _AtLeastServicePack _a _b _t _f
  !insertmacro __GetWinServicePack
  !insertmacro _>= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend

!define AtMostServicePack `"" AtMostServicePack`
!macro _AtMostServicePack _a _b _t _f
  !insertmacro __GetWinServicePack
  !insertmacro _<= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend

!define IsServicePack `"" IsServicePack`
!macro _IsServicePack _a _b _t _f
  !insertmacro __GetWinServicePack
  !insertmacro _= $_LOGICLIB_TEMP `${_b}` `${_t}` `${_f}`
!macroend


!endif # !___WINVER__NSH___

!verbose pop
