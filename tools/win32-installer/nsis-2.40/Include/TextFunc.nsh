/*
_____________________________________________________________________________

                       Text Functions Header v2.4
_____________________________________________________________________________

 2006 Shengalts Aleksander aka Instructor (Shengalts@mail.ru)

 See documentation for more information about the following functions.

 Usage in script:
 1. !include "TextFunc.nsh"
 2. !insertmacro TextFunction
 3. [Section|Function]
      ${TextFunction} "File" "..."  $var
    [SectionEnd|FunctionEnd]


 TextFunction=[LineFind|LineRead|FileReadFromEnd|LineSum|FileJoin|
               TextCompare|TextCompareS|ConfigRead|ConfigReadS|
               ConfigWrite|ConfigWriteS|FileRecode|TrimNewLines]

 un.TextFunction=[un.LineFind|un.LineRead|un.FileReadFromEnd|un.LineSum|
                  un.FileJoin|un.TextCompare|un.TextCompareS|un.ConfigRead|
                  un.ConfigReadS|un.ConfigWrite|un.ConfigWriteS|un.FileRecode|
                  un.TrimNewLines]

_____________________________________________________________________________

                       Thanks to:
_____________________________________________________________________________

LineRead
	Afrow UK (Based on his idea of Function "ReadFileLine")
LineSum
	Afrow UK (Based on his idea of Function "LineCount")
FileJoin
	Afrow UK (Based on his idea of Function "JoinFiles")
ConfigRead
	vbgunz (His idea)
ConfigWrite
	vbgunz (His idea)
TrimNewLines
	sunjammer (Based on his Function "TrimNewLines")
*/


;_____________________________________________________________________________
;
;                                   Macros
;_____________________________________________________________________________
;
; Change log window verbosity (default: 3=no script)
;
; Example:
; !include "TextFunc.nsh"
; !insertmacro LineFind
; ${TEXTFUNC_VERBOSE} 4   # all verbosity
; !insertmacro LineSum
; ${TEXTFUNC_VERBOSE} 3   # no script

!ifndef TEXTFUNC_INCLUDED
!define TEXTFUNC_INCLUDED

!include FileFunc.nsh

!verbose push
!verbose 3
!ifndef _TEXTFUNC_VERBOSE
	!define _TEXTFUNC_VERBOSE 3
!endif
!verbose ${_TEXTFUNC_VERBOSE}
!define TEXTFUNC_VERBOSE `!insertmacro TEXTFUNC_VERBOSE`
!define _TEXTFUNC_UN
!define _TEXTFUNC_S
!verbose pop

!macro TEXTFUNC_VERBOSE _VERBOSE
	!verbose push
	!verbose 3
	!undef _TEXTFUNC_VERBOSE
	!define _TEXTFUNC_VERBOSE ${_VERBOSE}
	!verbose pop
!macroend


# Install. Case insensitive. #

!macro LineFindCall _INPUT _OUTPUT _RANGE _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_INPUT}`
	Push `${_OUTPUT}`
	Push `${_RANGE}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call LineFind
	Pop $0
	!verbose pop
!macroend

!macro LineReadCall _FILE _NUMBER _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_NUMBER}`
	Call LineRead
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro FileReadFromEndCall _FILE _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call FileReadFromEnd
	Pop $0
	!verbose pop
!macroend

!macro LineSumCall _FILE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Call LineSum
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro FileJoinCall _FILE1 _FILE2 _FILE3
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_FILE3}`
	Call FileJoin
	!verbose pop
!macroend

!macro TextCompareCall _FILE1 _FILE2 _OPTION _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_OPTION}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call TextCompare
	Pop $0
	!verbose pop
!macroend

!macro ConfigReadCall _FILE _ENTRY _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Call ConfigRead
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro ConfigWriteCall _FILE _ENTRY _VALUE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Push `${_VALUE}`
	Call ConfigWrite
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro FileRecodeCall _FILE _FORMAT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_FORMAT}`
	Call FileRecode
	!verbose pop
!macroend

!macro TrimNewLinesCall _FILE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Call TrimNewLines
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro _TextFunc_TempFileForFile _FILE _RESULT
	${${_TEXTFUNC_UN}GetParent} ${_FILE} ${_RESULT}
	StrCmp ${_RESULT} "" 0 +2
		StrCpy ${_RESULT} $EXEDIR
	GetTempFileName ${_RESULT} ${_RESULT}
	StrCmp ${_RESULT} "" 0 +2
		GetTempFileName ${_RESULT}
	ClearErrors
!macroend

!macro LineFind
	!ifndef ${_TEXTFUNC_UN}LineFind
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}LineFind `!insertmacro ${_TEXTFUNC_UN}LineFindCall`

		!insertmacro ${_TEXTFUNC_UN}GetParent

		Function ${_TEXTFUNC_UN}LineFind
			Exch $3
			Exch
			Exch $2
			Exch
			Exch 2
			Exch $1
			Exch 2
			Exch 3
			Exch $0
			Exch 3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R4
			Push $R5
			Push $R6
			Push $R7
			Push $R8
			Push $R9
			ClearErrors

			IfFileExists '$0' 0 error
			StrCmp $1 '/NUL' begin
			StrCpy $8 0
			IntOp $8 $8 - 1
			StrCpy $9 $1 1 $8
			StrCmp $9 \ +2
			StrCmp $9 '' +3 -3
			StrCpy $9 $1 $8
			IfFileExists '$9\*.*' 0 error

			begin:
			StrCpy $4 1
			StrCpy $5 -1
			StrCpy $6 0
			StrCpy $7 0
			StrCpy $R4 ''
			StrCpy $R6 ''
			StrCpy $R7 ''
			StrCpy $R8 0

			StrCpy $8 $2 1
			StrCmp $8 '{' 0 delspaces
			StrCpy $2 $2 '' 1
			StrCpy $8 $2 1 -1
			StrCmp $8 '}' 0 delspaces
			StrCpy $2 $2 -1
			StrCpy $R6 cut

			delspaces:
			StrCpy $8 $2 1
			StrCmp $8 ' ' 0 +3
			StrCpy $2 $2 '' 1
			goto -3
			StrCmp $2$7 '0' file
			StrCpy $4 ''
			StrCpy $5 ''
			StrCmp $2 '' writechk

			range:
			StrCpy $8 0
			StrCpy $9 $2 1 $8
			StrCmp $9 '' +5
			StrCmp $9 ' ' +4
			StrCmp $9 ':' +3
			IntOp $8 $8 + 1
			goto -5
			StrCpy $5 $2 $8
			IntOp $5 $5 + 0
			IntOp $8 $8 + 1
			StrCpy $2 $2 '' $8
			StrCmp $4 '' 0 +2
			StrCpy $4 $5
			StrCmp $9 ':' range

			IntCmp $4 0 0 +2
			IntCmp $5 -1 goto 0 growthcmp
			StrCmp $R7 '' 0 minus2plus
			StrCpy $R7 0
			FileOpen $8 $0 r
			FileRead $8 $9
			IfErrors +3
			IntOp $R7 $R7 + 1
			Goto -3
			FileClose $8

			minus2plus:
			IntCmp $4 0 +5 0 +5
			IntOp $4 $R7 + $4
			IntOp $4 $4 + 1
			IntCmp $4 0 +2 0 +2
			StrCpy $4 0
			IntCmp $5 -1 goto 0 growthcmp
			IntOp $5 $R7 + $5
			IntOp $5 $5 + 1
			growthcmp:
			IntCmp $4 $5 goto goto
			StrCpy $5 $4
			goto:
			goto $7

			file:
			StrCmp $1 '/NUL' notemp
			!insertmacro _TextFunc_TempFileForFile $1 $R4
			Push $R4
			FileOpen $R4 $R4 w
			notemp:
			FileOpen $R5 $0 r
			IfErrors preerror

			loop:
			IntOp $R8 $R8 + 1
			FileRead $R5 $R9
			IfErrors handleclose

			cmp:
			StrCmp $2$4$5 '' writechk
			IntCmp $4 $R8 call 0 writechk
			StrCmp $5 -1 call
			IntCmp $5 $R8 call 0 call

			GetLabelAddress $7 cmp
			goto delspaces

			call:
			StrCpy $7 $R9
			Push $0
			Push $1
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $R4
			Push $R5
			Push $R6
			Push $R7
			Push $R8
			StrCpy $R6 '$4:$5'
			StrCmp $R7 '' +3
			IntOp $R7 $R8 - $R7
			IntOp $R7 $R7 - 1
			Call $3
			Pop $9
			Pop $R8
			Pop $R7
			Pop $R6
			Pop $R5
			Pop $R4
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
			IfErrors preerror
			StrCmp $9 'StopLineFind' 0 +3
			IntOp $6 $6 + 1
			goto handleclose
			StrCmp $1 '/NUL' loop
			StrCmp $9 'SkipWrite' 0 +3
			IntOp $6 $6 + 1
			goto loop
			StrCmp $7 $R9 write
			IntOp $6 $6 + 1
			goto write

			writechk:
			StrCmp $1 '/NUL' loop
			StrCmp $R6 cut 0 write
			IntOp $6 $6 + 1
			goto loop

			write:
			FileWrite $R4 $R9
			goto loop

			preerror:
			SetErrors

			handleclose:
			StrCmp $1 '/NUL' +3
			FileClose $R4
			Pop $R4
			FileClose $R5
			IfErrors error

			StrCmp $1 '/NUL' end
			StrCmp $1 '' 0 +2
			StrCpy $1 $0
			StrCmp $6 0 0 rename
			FileOpen $7 $0 r
			FileSeek $7 0 END $8
			FileClose $7
			FileOpen $7 $R4 r
			FileSeek $7 0 END $9
			FileClose $7
			IntCmp $8 $9 0 rename
			Delete $R4
			StrCmp $1 $0 end
			CopyFiles /SILENT $0 $1
			goto end

			rename:
			Delete '$EXEDIR\$1'
			Rename $R4 '$EXEDIR\$1'
			IfErrors 0 end
			Delete $1
			Rename $R4 $1
			IfErrors 0 end

			error:
			SetErrors

			end:
			Pop $R9
			Pop $R8
			Pop $R7
			Pop $R6
			Pop $R5
			Pop $R4
			Pop $9
			Pop $8
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro LineRead
	!ifndef ${_TEXTFUNC_UN}LineRead
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}LineRead `!insertmacro ${_TEXTFUNC_UN}LineReadCall`

		Function ${_TEXTFUNC_UN}LineRead
			Exch $1
			Exch
			Exch $0
			Exch
			Push $2
			Push $3
			Push $4
			ClearErrors

			IfFileExists $0 0 error
			IntOp $1 $1 + 0
			IntCmp $1 0 error 0 plus
			StrCpy $4 0
			FileOpen $2 $0 r
			IfErrors error
			FileRead $2 $3
			IfErrors +3
			IntOp $4 $4 + 1
			Goto -3
			FileClose $2
			IntOp $1 $4 + $1
			IntOp $1 $1 + 1
			IntCmp $1 0 error error

			plus:
			FileOpen $2 $0 r
			IfErrors error
			StrCpy $3 0
			IntOp $3 $3 + 1
			FileRead $2 $0
			IfErrors +4
			StrCmp $3 $1 0 -3
			FileClose $2
			goto end
			FileClose $2

			error:
			SetErrors
			StrCpy $0 ''

			end:
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Exch $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro FileReadFromEnd
	!ifndef ${_TEXTFUNC_UN}FileReadFromEnd
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}FileReadFromEnd `!insertmacro ${_TEXTFUNC_UN}FileReadFromEndCall`

		Function ${_TEXTFUNC_UN}FileReadFromEnd
			Exch $1
			Exch
			Exch $0
			Exch
			Push $7
			Push $8
			Push $9
			ClearErrors

			StrCpy $7 -1
			StrCpy $8 0
			IfFileExists $0 0 error
			FileOpen $0 $0 r
			IfErrors error
			FileRead $0 $9
			IfErrors +4
			Push $9
			IntOp $8 $8 + 1
			goto -4
			FileClose $0

			nextline:
			StrCmp $8 0 end
			Pop $9
			Push $1
			Push $7
			Push $8
			Call $1
			Pop $0
			Pop $8
			Pop $7
			Pop $1
			IntOp $7 $7 - 1
			IntOp $8 $8 - 1
			IfErrors error
			StrCmp $0 'StopFileReadFromEnd' clearstack nextline

			error:
			SetErrors

			clearstack:
			StrCmp $8 0 end
			Pop $9
			IntOp $8 $8 - 1
			goto clearstack

			end:
			Pop $9
			Pop $8
			Pop $7
			Pop $1
			Pop $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro LineSum
	!ifndef ${_TEXTFUNC_UN}LineSum
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}LineSum `!insertmacro ${_TEXTFUNC_UN}LineSumCall`

		Function ${_TEXTFUNC_UN}LineSum
			Exch $0
			Push $1
			Push $2
			ClearErrors

			IfFileExists $0 0 error
			StrCpy $2 0
			FileOpen $0 $0 r
			IfErrors error
			FileRead $0 $1
			IfErrors +3
			IntOp $2 $2 + 1
			Goto -3
			FileClose $0
			StrCpy $0 $2
			goto end

			error:
			SetErrors
			StrCpy $0 ''

			end:
			Pop $2
			Pop $1
			Exch $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro FileJoin
	!ifndef ${_TEXTFUNC_UN}FileJoin
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}FileJoin `!insertmacro ${_TEXTFUNC_UN}FileJoinCall`

		!insertmacro ${_TEXTFUNC_UN}GetParent

		Function ${_TEXTFUNC_UN}FileJoin
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Push $3
			Push $4
			Push $5
			ClearErrors

			IfFileExists $0 0 error
			IfFileExists $1 0 error
			StrCpy $3 0
			IntOp $3 $3 - 1
			StrCpy $4 $2 1 $3
			StrCmp $4 \ +2
			StrCmp $4 '' +3 -3
			StrCpy $4 $2 $3
			IfFileExists '$4\*.*' 0 error

			StrCmp $2 $0 0 +2
			StrCpy $2 ''
			StrCmp $2 '' 0 +3
			StrCpy $4 $0
			Goto notemp
			!insertmacro _TextFunc_TempFileForFile $2 $4
			CopyFiles /SILENT $0 $4
			notemp:
			FileOpen $3 $4 a
			IfErrors error
			FileSeek $3 -1 END
			FileRead $3 $5
			StrCmp $5 '$\r' +3
			StrCmp $5 '$\n' +2
			FileWrite $3 '$\r$\n'

			;FileWrite $3 '$\r$\n--Divider--$\r$\n'

			FileOpen $0 $1 r
			IfErrors error
			FileRead $0 $5
			IfErrors +3
			FileWrite $3 $5
			goto -3
			FileClose $0
			FileClose $3
			StrCmp $2 '' end
			Delete '$EXEDIR\$2'
			Rename $4 '$EXEDIR\$2'
			IfErrors 0 end
			Delete $2
			Rename $4 $2
			IfErrors 0 end

			error:
			SetErrors

			end:
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro TextCompare
	!ifndef ${_TEXTFUNC_UN}TextCompare${_TEXTFUNC_S}
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}TextCompare${_TEXTFUNC_S} `!insertmacro ${_TEXTFUNC_UN}TextCompare${_TEXTFUNC_S}Call`

		Function ${_TEXTFUNC_UN}TextCompare${_TEXTFUNC_S}
			Exch $3
			Exch
			Exch $2
			Exch
			Exch 2
			Exch $1
			Exch 2
			Exch 3
			Exch $0
			Exch 3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			ClearErrors

			IfFileExists $0 0 error
			IfFileExists $1 0 error
			StrCmp $2 'FastDiff' +5
			StrCmp $2 'FastEqual' +4
			StrCmp $2 'SlowDiff' +3
			StrCmp $2 'SlowEqual' +2
			goto error

			FileOpen $4 $0 r
			IfErrors error
			FileOpen $5 $1 r
			IfErrors error
			SetDetailsPrint textonly

			StrCpy $6 0
			StrCpy $8 0

			nextline:
			StrCmp${_TEXTFUNC_S} $4 '' fast
			IntOp $8 $8 + 1
			FileRead $4 $9
			IfErrors 0 +4
			FileClose $4
			StrCpy $4 ''
			StrCmp${_TEXTFUNC_S} $5 '' end
			StrCmp $2 'FastDiff' fast
			StrCmp $2 'FastEqual' fast slow

			fast:
			StrCmp${_TEXTFUNC_S} $5 '' call
			IntOp $6 $6 + 1
			FileRead $5 $7
			IfErrors 0 +5
			FileClose $5
			StrCpy $5 ''
			StrCmp${_TEXTFUNC_S} $4 '' end
			StrCmp $2 'FastDiff' call close
			StrCmp $2 'FastDiff' 0 +2
			StrCmp${_TEXTFUNC_S} $7 $9 nextline call
			StrCmp${_TEXTFUNC_S} $7 $9 call nextline

			slow:
			StrCmp${_TEXTFUNC_S} $4 '' close
			StrCpy $6 ''
			DetailPrint '$8. $9'
			FileSeek $5 0

			slownext:
			FileRead $5 $7
			IfErrors 0 +2
			StrCmp $2 'SlowDiff' call nextline
			StrCmp $2 'SlowDiff' 0 +2
			StrCmp${_TEXTFUNC_S} $7 $9 nextline slownext
			IntOp $6 $6 + 1
			StrCmp${_TEXTFUNC_S} $7 $9 0 slownext

			call:
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Call $3
			Pop $0
			Pop $9
			Pop $8
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			StrCmp $0 'StopTextCompare' 0 nextline

			close:
			FileClose $4
			FileClose $5
			goto end

			error:
			SetErrors

			end:
			SetDetailsPrint both
			Pop $9
			Pop $8
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro ConfigRead
	!ifndef ${_TEXTFUNC_UN}ConfigRead${_TEXTFUNC_S}
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}ConfigRead${_TEXTFUNC_S} `!insertmacro ${_TEXTFUNC_UN}ConfigRead${_TEXTFUNC_S}Call`

		Function ${_TEXTFUNC_UN}ConfigRead${_TEXTFUNC_S}
			Exch $1
			Exch
			Exch $0
			Exch
			Push $2
			Push $3
			Push $4
			ClearErrors

			FileOpen $2 $0 r
			IfErrors error
			StrLen $0 $1
			StrCmp${_TEXTFUNC_S} $0 0 error

			readnext:
			FileRead $2 $3
			IfErrors error
			StrCpy $4 $3 $0
			StrCmp${_TEXTFUNC_S} $4 $1 0 readnext
			StrCpy $0 $3 '' $0
			StrCpy $4 $0 1 -1
			StrCmp${_TEXTFUNC_S} $4 '$\r' +2
			StrCmp${_TEXTFUNC_S} $4 '$\n' 0 close
			StrCpy $0 $0 -1
			goto -4

			error:
			SetErrors
			StrCpy $0 ''

			close:
			FileClose $2

			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Exch $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro ConfigWrite
	!ifndef ${_TEXTFUNC_UN}ConfigWrite${_TEXTFUNC_S}
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}ConfigWrite${_TEXTFUNC_S} `!insertmacro ${_TEXTFUNC_UN}ConfigWrite${_TEXTFUNC_S}Call`

		Function ${_TEXTFUNC_UN}ConfigWrite${_TEXTFUNC_S}
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Push $3
			Push $4
			Push $5
			Push $6
			ClearErrors

			IfFileExists $0 0 error
			FileOpen $3 $0 a
			IfErrors error

			StrLen $0 $1
			StrCmp${_TEXTFUNC_S} $0 0 0 readnext
			StrCpy $0 ''
			goto close

			readnext:
			FileRead $3 $4
			IfErrors add
			StrCpy $5 $4 $0
			StrCmp${_TEXTFUNC_S} $5 $1 0 readnext

			StrCpy $5 0
			IntOp $5 $5 - 1
			StrCpy $6 $4 1 $5
			StrCmp${_TEXTFUNC_S} $6 '$\r' -2
			StrCmp${_TEXTFUNC_S} $6 '$\n' -3
			StrCpy $6 $4
			StrCmp${_TEXTFUNC_S} $5 -1 +3
			IntOp $5 $5 + 1
			StrCpy $6 $4 $5

			StrCmp${_TEXTFUNC_S} $2 '' change
			StrCmp${_TEXTFUNC_S} $6 '$1$2' 0 change
			StrCpy $0 SAME
			goto close

			change:
			FileSeek $3 0 CUR $5
			StrLen $4 $4
			IntOp $4 $5 - $4
			FileSeek $3 0 END $6
			IntOp $6 $6 - $5

			System::Alloc /NOUNLOAD $6
			Pop $0
			FileSeek $3 $5 SET
			System::Call /NOUNLOAD 'kernel32::ReadFile(i r3, i r0, i $6, t.,)'
			FileSeek $3 $4 SET
			StrCmp${_TEXTFUNC_S} $2 '' +2
			FileWrite $3 '$1$2$\r$\n'
			System::Call /NOUNLOAD 'kernel32::WriteFile(i r3, i r0, i $6, t.,)'
			System::Call /NOUNLOAD 'kernel32::SetEndOfFile(i r3)'
			System::Free $0
			StrCmp${_TEXTFUNC_S} $2 '' +3
			StrCpy $0 CHANGED
			goto close
			StrCpy $0 DELETED
			goto close

			add:
			StrCmp${_TEXTFUNC_S} $2 '' 0 +3
			StrCpy $0 SAME
			goto close
			FileSeek $3 -1 END
			FileRead $3 $4
			IfErrors +4
			StrCmp${_TEXTFUNC_S} $4 '$\r' +3
			StrCmp${_TEXTFUNC_S} $4 '$\n' +2
			FileWrite $3 '$\r$\n'
			FileWrite $3 '$1$2$\r$\n'
			StrCpy $0 ADDED

			close:
			FileClose $3
			goto end

			error:
			SetErrors
			StrCpy $0 ''

			end:
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Exch $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro FileRecode
	!ifndef ${_TEXTFUNC_UN}FileRecode
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}FileRecode `!insertmacro ${_TEXTFUNC_UN}FileRecodeCall`

		Function ${_TEXTFUNC_UN}FileRecode
			Exch $1
			Exch
			Exch $0
			Exch
			Push $2
			Push $3
			Push $4

			IfFileExists $0 0 error
			StrCmp $1 OemToChar +2
			StrCmp $1 CharToOem 0 error

			FileOpen $2 $0 a
			FileSeek $2 0 END $3
			System::Alloc /NOUNLOAD $3
			Pop $4
			FileSeek $2 0 SET
			System::Call /NOUNLOAD 'kernel32::ReadFile(i r2, i r4, i $3, t.,)'
			System::Call /NOUNLOAD 'user32::$1Buff(i r4, i r4, i $3)'
			FileSeek $2 0 SET
			System::Call /NOUNLOAD 'kernel32::WriteFile(i r2, i r4, i $3, t.,)'
			System::Free $4
			FileClose $2
			goto end

			error:
			SetErrors

			end:
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro TrimNewLines
	!ifndef ${_TEXTFUNC_UN}TrimNewLines
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!define ${_TEXTFUNC_UN}TrimNewLines `!insertmacro ${_TEXTFUNC_UN}TrimNewLinesCall`

		Function ${_TEXTFUNC_UN}TrimNewLines
			Exch $0
			Push $1
			Push $2

			StrCpy $1 0
			IntOp $1 $1 - 1
			StrCpy $2 $0 1 $1
			StrCmp $2 '$\r' -2
			StrCmp $2 '$\n' -3
			StrCmp $1 -1 +3
			IntOp $1 $1 + 1
			StrCpy $0 $0 $1

			Pop $2
			Pop $1
			Exch $0
		FunctionEnd

		!verbose pop
	!endif
!macroend


# Uninstall. Case insensitive. #

!macro un.LineFindCall _INPUT _OUTPUT _RANGE _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_INPUT}`
	Push `${_OUTPUT}`
	Push `${_RANGE}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call un.LineFind
	Pop $0
	!verbose pop
!macroend

!macro un.LineReadCall _FILE _NUMBER _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_NUMBER}`
	Call un.LineRead
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.FileReadFromEndCall _FILE _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call un.FileReadFromEnd
	Pop $0
	!verbose pop
!macroend

!macro un.LineSumCall _FILE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Call un.LineSum
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.FileJoinCall _FILE1 _FILE2 _FILE3
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_FILE3}`
	Call un.FileJoin
	!verbose pop
!macroend

!macro un.TextCompareCall _FILE1 _FILE2 _OPTION _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_OPTION}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call un.TextCompare
	Pop $0
	!verbose pop
!macroend

!macro un.ConfigReadCall _FILE _ENTRY _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Call un.ConfigRead
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.ConfigWriteCall _FILE _ENTRY _VALUE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Push `${_VALUE}`
	Call un.ConfigWrite
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.FileRecodeCall _FILE _FORMAT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_FORMAT}`
	Call un.FileRecode
	!verbose pop
!macroend

!macro un.TrimNewLinesCall _FILE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Call un.TrimNewLines
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.LineFind
	!ifndef un.LineFind
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro LineFind

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.LineRead
	!ifndef un.LineRead
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro LineRead

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.FileReadFromEnd
	!ifndef un.FileReadFromEnd
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro FileReadFromEnd

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.LineSum
	!ifndef un.LineSum
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro LineSum

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.FileJoin
	!ifndef un.FileJoin
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro FileJoin

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.TextCompare
	!ifndef un.TextCompare
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro TextCompare

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.ConfigRead
	!ifndef un.ConfigRead
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro ConfigRead

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.ConfigWrite
	!ifndef un.ConfigWrite
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro ConfigWrite

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.FileRecode
	!ifndef un.FileRecode
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro FileRecode

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.TrimNewLines
	!ifndef un.TrimNewLines
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`

		!insertmacro TrimNewLines

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!verbose pop
	!endif
!macroend


# Install. Case sensitive. #

!macro TextCompareSCall _FILE1 _FILE2 _OPTION _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_OPTION}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call TextCompareS
	Pop $0
	!verbose pop
!macroend

!macro ConfigReadSCall _FILE _ENTRY _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Call ConfigReadS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro ConfigWriteSCall _FILE _ENTRY _VALUE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Push `${_VALUE}`
	Call ConfigWriteS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro TextCompareS
	!ifndef TextCompareS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro TextCompare

		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend

!macro ConfigReadS
	!ifndef ConfigReadS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro ConfigRead

		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend

!macro ConfigWriteS
	!ifndef ConfigWriteS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro ConfigWrite

		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend


# Uninstall. Case sensitive. #

!macro un.TextCompareSCall _FILE1 _FILE2 _OPTION _FUNC
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push $0
	Push `${_FILE1}`
	Push `${_FILE2}`
	Push `${_OPTION}`
	GetFunctionAddress $0 `${_FUNC}`
	Push `$0`
	Call un.TextCompareS
	Pop $0
	!verbose pop
!macroend

!macro un.ConfigReadSCall _FILE _ENTRY _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Call un.ConfigReadS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.ConfigWriteSCall _FILE _ENTRY _VALUE _RESULT
	!verbose push
	!verbose ${_TEXTFUNC_VERBOSE}
	Push `${_FILE}`
	Push `${_ENTRY}`
	Push `${_VALUE}`
	Call un.ConfigWriteS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.TextCompareS
	!ifndef un.TextCompareS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro TextCompare

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.ConfigReadS
	!ifndef un.ConfigReadS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro ConfigRead

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.ConfigWriteS
	!ifndef un.ConfigWriteS
		!verbose push
		!verbose ${_TEXTFUNC_VERBOSE}
		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN `un.`
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S `S`

		!insertmacro ConfigWrite

		!undef _TEXTFUNC_UN
		!define _TEXTFUNC_UN
		!undef _TEXTFUNC_S
		!define _TEXTFUNC_S
		!verbose pop
	!endif
!macroend

!endif
