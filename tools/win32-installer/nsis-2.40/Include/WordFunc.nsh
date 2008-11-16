/*
_____________________________________________________________________________

                       Word Functions Header v3.3
_____________________________________________________________________________

 2006 Shengalts Aleksander aka Instructor (Shengalts@mail.ru)

 See documentation for more information about the following functions.

 Usage in script:
 1. !include "WordFunc.nsh"
 2. !insertmacro WordFunction
 3. [Section|Function]
      ${WordFunction} "Param1" "Param2" "..." $var
    [SectionEnd|FunctionEnd]


 WordFunction=[WordFind|WordFindS|WordFind2X|WordFind2XS|WordFind3X|WordFind3XS|
               WordReplace|WordReplaceS|WordAdd|WordAddS|WordInsert|WordInsertS|
               StrFilter|StrFilterS|VersionCompare|VersionConvert]

 un.WordFunction=[un.WordFind|un.WordFindS|un.WordFind2X|un.WordFind2XS|
                  un.WordFind3X|un.WordFind3XS|un.WordReplace|un.WordReplaceS|
                  un.WordAdd|un.WordAddS|un.WordInsert|un.WordInsertS|
                  un.StrFilter|un.StrFilterS|un.VersionCompare|un.VersionConvert]

_____________________________________________________________________________

                       Thanks to:
_____________________________________________________________________________

WordFind3X
	Afrow UK (Based on his idea of Function "StrSortLR")
StrFilter
	sunjammer (Function "StrUpper")
VersionCompare
	Afrow UK (Based on his Function "VersionCheckNew2")
VersionConvert
	Afrow UK (Based on his idea of Function "CharIndexReplace")
*/


;_____________________________________________________________________________
;
;                         Macros
;_____________________________________________________________________________
;
; Change log window verbosity (default: 3=no script)
;
; Example:
; !include "WordFunc.nsh"
; !insertmacro WordFind
; ${WORDFUNC_VERBOSE} 4   # all verbosity
; !insertmacro WordReplace
; ${WORDFUNC_VERBOSE} 3   # no script

!ifndef WORDFUNC_INCLUDED
!define WORDFUNC_INCLUDED

!verbose push
!verbose 3
!ifndef _WORDFUNC_VERBOSE
	!define _WORDFUNC_VERBOSE 3
!endif
!verbose ${_WORDFUNC_VERBOSE}
!define WORDFUNC_VERBOSE `!insertmacro WORDFUNC_VERBOSE`
!define _WORDFUNC_UN
!define _WORDFUNC_S
!verbose pop

!macro WORDFUNC_VERBOSE _VERBOSE
	!verbose push
	!verbose 3
	!undef _WORDFUNC_VERBOSE
	!define _WORDFUNC_VERBOSE ${_VERBOSE}
	!verbose pop
!macroend


# Install. Case insensitive. #

!macro WordFindCall _STRING _DELIMITER _OPTION _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_OPTION}`
	Call WordFind
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFind2XCall _STRING _DELIMITER1 _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call WordFind2X
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFind3XCall _STRING _DELIMITER1 _CENTER _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_CENTER}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call WordFind3X
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordReplaceCall _STRING _WORD1 _WORD2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_WORD1}`
	Push `${_WORD2}`
	Push `${_NUMBER}`
	Call WordReplace
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordAddCall _STRING1 _DELIMITER _STRING2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING1}`
	Push `${_DELIMITER}`
	Push `${_STRING2}`
	Call WordAdd
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordInsertCall _STRING _DELIMITER _WORD _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_WORD}`
	Push `${_NUMBER}`
	Call WordInsert
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro StrFilterCall _STRING _FILTER _INCLUDE _EXCLUDE _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_FILTER}`
	Push `${_INCLUDE}`
	Push `${_EXCLUDE}`
	Call StrFilter
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro VersionCompareCall _VER1 _VER2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_VER1}`
	Push `${_VER2}`
	Call VersionCompare
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro VersionConvertCall _VERSION _CHARLIST _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_VERSION}`
	Push `${_CHARLIST}`
	Call VersionConvert
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFind
	!ifndef ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}WordFind${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
			Exch $1
			Exch
			Exch $0
			Exch
			Exch 2
			Exch $R0
			Exch 2
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R1
			Push $R2
			ClearErrors

			StrCpy $9 ''
			StrCpy $2 $1 1
			StrCpy $1 $1 '' 1
			StrCmp $2 'E' 0 +3
			StrCpy $9 E
			goto -4

			StrCpy $3 ''
			StrCmp${_WORDFUNC_S} $2 '+' +6
			StrCmp${_WORDFUNC_S} $2 '-' +5
			StrCmp${_WORDFUNC_S} $2 '/' restart
			StrCmp${_WORDFUNC_S} $2 '#' restart
			StrCmp${_WORDFUNC_S} $2 '*' restart
			goto error3

			StrCpy $4 $1 1 -1
			StrCmp${_WORDFUNC_S} $4 '*' +4
			StrCmp${_WORDFUNC_S} $4 '}' +3
			StrCmp${_WORDFUNC_S} $4 '{' +2
			goto +4
			StrCpy $1 $1 -1
			StrCpy $3 '$4$3'
			goto -7
			StrCmp${_WORDFUNC_S} $3 '*' error3
			StrCmp${_WORDFUNC_S} $3 '**' error3
			StrCmp${_WORDFUNC_S} $3 '}{' error3
			IntOp $1 $1 + 0
			StrCmp${_WORDFUNC_S} $1 0 error2

			restart:
			StrCmp${_WORDFUNC_S} $R0 '' error1
			StrCpy $4 0
			StrCpy $5 0
			StrCpy $6 0
			StrLen $7 $0
			goto loop

			preloop:
			IntOp $6 $6 + 1

			loop:
			StrCpy $8 $R0 $7 $6
			StrCmp${_WORDFUNC_S} $8$5 0 error1
			StrLen $R2 $8
			IntCmp $R2 0 +2
			StrCmp${_WORDFUNC_S} $8 $0 +5 preloop
			StrCmp${_WORDFUNC_S} $3 '{' minus
			StrCmp${_WORDFUNC_S} $3 '}' minus
			StrCmp${_WORDFUNC_S} $2 '*' minus
			StrCmp${_WORDFUNC_S} $5 $6 minus +5
			StrCmp${_WORDFUNC_S} $3 '{' +4
			StrCmp${_WORDFUNC_S} $3 '}' +3
			StrCmp${_WORDFUNC_S} $2 '*' +2
			StrCmp${_WORDFUNC_S} $5 $6 nextword
			IntOp $4 $4 + 1
			StrCmp${_WORDFUNC_S} $2$4 +$1 plus
			StrCmp${_WORDFUNC_S} $2 '/' 0 nextword
			IntOp $8 $6 - $5
			StrCpy $8 $R0 $8 $5
			StrCmp${_WORDFUNC_S} $1 $8 0 nextword
			StrCpy $R1 $4
			goto end
			nextword:
			IntOp $6 $6 + $7
			StrCpy $5 $6
			goto loop

			minus:
			StrCmp${_WORDFUNC_S} $2 '-' 0 sum
			StrCpy $2 '+'
			IntOp $1 $4 - $1
			IntOp $1 $1 + 1
			IntCmp $1 0 error2 error2 restart
			sum:
			StrCmp${_WORDFUNC_S} $2 '#' 0 sumdelim
			StrCpy $R1 $4
			goto end
			sumdelim:
			StrCmp${_WORDFUNC_S} $2 '*' 0 error2
			StrCpy $R1 $4
			goto end

			plus:
			StrCmp${_WORDFUNC_S} $3 '' 0 +4
			IntOp $6 $6 - $5
			StrCpy $R1 $R0 $6 $5
			goto end
			StrCmp${_WORDFUNC_S} $3 '{' 0 +3
			StrCpy $R1 $R0 $6
			goto end
			StrCmp${_WORDFUNC_S} $3 '}' 0 +4
			IntOp $6 $6 + $7
			StrCpy $R1 $R0 '' $6
			goto end
			StrCmp${_WORDFUNC_S} $3 '{*' +2
			StrCmp${_WORDFUNC_S} $3 '*{' 0 +3
			StrCpy $R1 $R0 $6
			goto end
			StrCmp${_WORDFUNC_S} $3 '*}' +2
			StrCmp${_WORDFUNC_S} $3 '}*' 0 +3
			StrCpy $R1 $R0 '' $5
			goto end
			StrCmp${_WORDFUNC_S} $3 '}}' 0 +3
			StrCpy $R1 $R0 '' $6
			goto end
			StrCmp${_WORDFUNC_S} $3 '{{' 0 +3
			StrCpy $R1 $R0 $5
			goto end
			StrCmp${_WORDFUNC_S} $3 '{}' 0 error3
			StrLen $3 $R0
			StrCmp${_WORDFUNC_S} $3 $6 0 +3
			StrCpy $0 ''
			goto +2
			IntOp $6 $6 + $7
			StrCpy $8 $R0 '' $6
			StrCmp${_WORDFUNC_S} $4$8 1 +6
			StrCmp${_WORDFUNC_S} $4 1 +2 +7
			IntOp $6 $6 + $7
			StrCpy $3 $R0 $7 $6
			StrCmp${_WORDFUNC_S} $3 '' +2
			StrCmp${_WORDFUNC_S} $3 $0 -3 +3
			StrCpy $R1 ''
			goto end
			StrCmp${_WORDFUNC_S} $5 0 0 +3
			StrCpy $0 ''
			goto +2
			IntOp $5 $5 - $7
			StrCpy $3 $R0 $5
			StrCpy $R1 '$3$0$8'
			goto end

			error3:
			StrCpy $R1 3
			goto error
			error2:
			StrCpy $R1 2
			goto error
			error1:
			StrCpy $R1 1
			error:
			StrCmp $9 'E' 0 +3
			SetErrors

			end:
			StrCpy $R0 $R1

			Pop $R2
			Pop $R1
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
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro WordFind2X
	!ifndef ${_WORDFUNC_UN}WordFind2X${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}WordFind2X${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordFind2X${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordFind2X${_WORDFUNC_S}
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Exch 3
			Exch $R0
			Exch 3
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R1
			Push $R2
			ClearErrors

			StrCpy $R2 ''
			StrCpy $3 $2 1
			StrCpy $2 $2 '' 1
			StrCmp $3 'E' 0 +3
			StrCpy $R2 E
			goto -4

			StrCmp${_WORDFUNC_S} $3 '+' +5
			StrCmp${_WORDFUNC_S} $3 '-' +4
			StrCmp${_WORDFUNC_S} $3 '#' restart
			StrCmp${_WORDFUNC_S} $3 '/' restart
			goto error3

			StrCpy $4 $2 2 -2
			StrCmp${_WORDFUNC_S} $4 '{{' +9
			StrCmp${_WORDFUNC_S} $4 '}}' +8
			StrCmp${_WORDFUNC_S} $4 '{*' +7
			StrCmp${_WORDFUNC_S} $4 '*{' +6
			StrCmp${_WORDFUNC_S} $4 '*}' +5
			StrCmp${_WORDFUNC_S} $4 '}*' +4
			StrCmp${_WORDFUNC_S} $4 '{}' +3
			StrCpy $4 ''
			goto +2
			StrCpy $2 $2 -2
			IntOp $2 $2 + 0
			StrCmp${_WORDFUNC_S} $2 0 error2

			restart:
			StrCmp${_WORDFUNC_S} $R0 '' error1
			StrCpy $5 -1
			StrCpy $6 0
			StrCpy $7 ''
			StrLen $8 $0
			StrLen $9 $1

			loop:
			IntOp $5 $5 + 1

			delim1:
			StrCpy $R1 $R0 $8 $5
			StrCmp${_WORDFUNC_S} $R1$6 0 error1
			StrCmp${_WORDFUNC_S} $R1 '' minus
			StrCmp${_WORDFUNC_S} $R1 $0 +2
			StrCmp${_WORDFUNC_S} $7 '' loop delim2
			StrCmp${_WORDFUNC_S} $0 $1 0 +2
			StrCmp${_WORDFUNC_S} $7 '' 0 delim2
			IntOp $7 $5 + $8
			StrCpy $5 $7
			goto delim1

			delim2:
			StrCpy $R1 $R0 $9 $5
			StrCmp${_WORDFUNC_S} $R1 $1 0 loop
			IntOp $6 $6 + 1
			StrCmp${_WORDFUNC_S} $3$6 '+$2' plus
			StrCmp${_WORDFUNC_S} $3 '/' 0 nextword
			IntOp $R1 $5 - $7
			StrCpy $R1 $R0 $R1 $7
			StrCmp${_WORDFUNC_S} $R1 $2 0 +3
			StrCpy $R1 $6
			goto end
			nextword:
			IntOp $5 $5 + $9
			StrCpy $7 ''
			goto delim1

			minus:
			StrCmp${_WORDFUNC_S} $3 '-' 0 sum
			StrCpy $3 +
			IntOp $2 $6 - $2
			IntOp $2 $2 + 1
			IntCmp $2 0 error2 error2 restart
			sum:
			StrCmp${_WORDFUNC_S} $3 '#' 0 error2
			StrCpy $R1 $6
			goto end

			plus:
			StrCmp${_WORDFUNC_S} $4 '' 0 +4
			IntOp $R1 $5 - $7
			StrCpy $R1 $R0 $R1 $7
			goto end
			IntOp $5 $5 + $9
			IntOp $7 $7 - $8
			StrCmp${_WORDFUNC_S} $4 '{*' +2
			StrCmp${_WORDFUNC_S} $4 '*{' 0 +3
			StrCpy $R1 $R0 $5
			goto end
			StrCmp${_WORDFUNC_S} $4 '*}' +2
			StrCmp${_WORDFUNC_S} $4 '}*' 0 +3
			StrCpy $R1 $R0 '' $7
			goto end
			StrCmp${_WORDFUNC_S} $4 '}}' 0 +3
			StrCpy $R1 $R0 '' $5
			goto end
			StrCmp${_WORDFUNC_S} $4 '{{' 0 +3
			StrCpy $R1 $R0 $7
			goto end
			StrCmp${_WORDFUNC_S} $4 '{}' 0 error3
			StrCpy $5 $R0 '' $5
			StrCpy $7 $R0 $7
			StrCpy $R1 '$7$5'
			goto end

			error3:
			StrCpy $R1 3
			goto error
			error2:
			StrCpy $R1 2
			goto error
			error1:
			StrCpy $R1 1
			error:
			StrCmp $R2 'E' 0 +3
			SetErrors

			end:
			StrCpy $R0 $R1

			Pop $R2
			Pop $R1
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
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro WordFind3X
	!ifndef ${_WORDFUNC_UN}WordFind3X${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}WordFind3X${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordFind3X${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordFind3X${_WORDFUNC_S}
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
			Exch 4
			Exch $R0
			Exch 4
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R1
			Push $R2
			Push $R3
			Push $R4
			Push $R5
			ClearErrors

			StrCpy $R5 ''
			StrCpy $4 $3 1
			StrCpy $3 $3 '' 1
			StrCmp $4 'E' 0 +3
			StrCpy $R5 E
			goto -4

			StrCmp${_WORDFUNC_S} $4 '+' +5
			StrCmp${_WORDFUNC_S} $4 '-' +4
			StrCmp${_WORDFUNC_S} $4 '#' restart
			StrCmp${_WORDFUNC_S} $4 '/' restart
			goto error3

			StrCpy $5 $3 2 -2
			StrCmp${_WORDFUNC_S} $5 '{{' +9
			StrCmp${_WORDFUNC_S} $5 '}}' +8
			StrCmp${_WORDFUNC_S} $5 '{*' +7
			StrCmp${_WORDFUNC_S} $5 '*{' +6
			StrCmp${_WORDFUNC_S} $5 '*}' +5
			StrCmp${_WORDFUNC_S} $5 '}*' +4
			StrCmp${_WORDFUNC_S} $5 '{}' +3
			StrCpy $5 ''
			goto +2
			StrCpy $3 $3 -2
			IntOp $3 $3 + 0
			StrCmp${_WORDFUNC_S} $3 0 error2

			restart:
			StrCmp${_WORDFUNC_S} $R0 '' error1
			StrCpy $6 -1
			StrCpy $7 0
			StrCpy $8 ''
			StrCpy $9 ''
			StrLen $R1 $0
			StrLen $R2 $1
			StrLen $R3 $2

			loop:
			IntOp $6 $6 + 1

			delim1:
			StrCpy $R4 $R0 $R1 $6
			StrCmp${_WORDFUNC_S} $R4$7 0 error1
			StrCmp${_WORDFUNC_S} $R4 '' minus
			StrCmp${_WORDFUNC_S} $R4 $0 +2
			StrCmp${_WORDFUNC_S} $8 '' loop center
			StrCmp${_WORDFUNC_S} $0 $1 +2
			StrCmp${_WORDFUNC_S} $0 $2 0 +2
			StrCmp${_WORDFUNC_S} $8 '' 0 center
			IntOp $8 $6 + $R1
			StrCpy $6 $8
			goto delim1

			center:
			StrCmp${_WORDFUNC_S} $9 '' 0 delim2
			StrCpy $R4 $R0 $R2 $6
			StrCmp${_WORDFUNC_S} $R4 $1 0 loop
			IntOp $9 $6 + $R2
			StrCpy $6 $9
			goto delim1

			delim2:
			StrCpy $R4 $R0 $R3 $6
			StrCmp${_WORDFUNC_S} $R4 $2 0 loop
			IntOp $7 $7 + 1
			StrCmp${_WORDFUNC_S} $4$7 '+$3' plus
			StrCmp${_WORDFUNC_S} $4 '/' 0 nextword
			IntOp $R4 $6 - $8
			StrCpy $R4 $R0 $R4 $8
			StrCmp${_WORDFUNC_S} $R4 $3 0 +3
			StrCpy $R4 $7
			goto end
			nextword:
			IntOp $6 $6 + $R3
			StrCpy $8 ''
			StrCpy $9 ''
			goto delim1

			minus:
			StrCmp${_WORDFUNC_S} $4 '-' 0 sum
			StrCpy $4 +
			IntOp $3 $7 - $3
			IntOp $3 $3 + 1
			IntCmp $3 0 error2 error2 restart
			sum:
			StrCmp${_WORDFUNC_S} $4 '#' 0 error2
			StrCpy $R4 $7
			goto end

			plus:
			StrCmp${_WORDFUNC_S} $5 '' 0 +4
			IntOp $R4 $6 - $8
			StrCpy $R4 $R0 $R4 $8
			goto end
			IntOp $6 $6 + $R3
			IntOp $8 $8 - $R1
			StrCmp${_WORDFUNC_S} $5 '{*' +2
			StrCmp${_WORDFUNC_S} $5 '*{' 0 +3
			StrCpy $R4 $R0 $6
			goto end
			StrCmp${_WORDFUNC_S} $5 '*}' +2
			StrCmp${_WORDFUNC_S} $5 '}*' 0 +3
			StrCpy $R4 $R0 '' $8
			goto end
			StrCmp${_WORDFUNC_S} $5 '}}' 0 +3
			StrCpy $R4 $R0 '' $6
			goto end
			StrCmp${_WORDFUNC_S} $5 '{{' 0 +3
			StrCpy $R4 $R0 $8
			goto end
			StrCmp${_WORDFUNC_S} $5 '{}' 0 error3
			StrCpy $6 $R0 '' $6
			StrCpy $8 $R0 $8
			StrCpy $R4 '$8$6'
			goto end

			error3:
			StrCpy $R4 3
			goto error
			error2:
			StrCpy $R4 2
			goto error
			error1:
			StrCpy $R4 1
			error:
			StrCmp $R5 'E' 0 +3
			SetErrors

			end:
			StrCpy $R0 $R4
			Pop $R5
			Pop $R4
			Pop $R3
			Pop $R2
			Pop $R1
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
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro WordReplace
	!ifndef ${_WORDFUNC_UN}WordReplace${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}WordReplace${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordReplace${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordReplace${_WORDFUNC_S}
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Exch 3
			Exch $R0
			Exch 3
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R1
			ClearErrors

			StrCpy $R1 $R0
			StrCpy $9 ''
			StrCpy $3 $2 1
			StrCpy $2 $2 '' 1
			StrCmp $3 'E' 0 +3
			StrCpy $9 E
			goto -4

			StrCpy $4 $2 1 -1
			StrCpy $5 ''
			StrCpy $6 ''
			StrLen $7 $0

			StrCmp${_WORDFUNC_S} $7 0 error1
			StrCmp${_WORDFUNC_S} $R0 '' error1
			StrCmp${_WORDFUNC_S} $3 '{' beginning
			StrCmp${_WORDFUNC_S} $3 '}' ending errorchk

			beginning:
			StrCpy $8 $R0 $7
			StrCmp${_WORDFUNC_S} $8 $0 0 +4
			StrCpy $R0 $R0 '' $7
			StrCpy $5 '$5$1'
			goto -4
			StrCpy $3 $2 1
			StrCmp${_WORDFUNC_S} $3 '}' 0 merge

			ending:
			StrCpy $8 $R0 '' -$7
			StrCmp${_WORDFUNC_S} $8 $0 0 +4
			StrCpy $R0 $R0 -$7
			StrCpy $6 '$6$1'
			goto -4

			merge:
			StrCmp${_WORDFUNC_S} $4 '*' 0 +5
			StrCmp${_WORDFUNC_S} $5 '' +2
			StrCpy $5 $1
			StrCmp${_WORDFUNC_S} $6 '' +2
			StrCpy $6 $1
			StrCpy $R0 '$5$R0$6'
			goto end

			errorchk:
			StrCmp${_WORDFUNC_S} $3 '+' +2
			StrCmp${_WORDFUNC_S} $3 '-' 0 error3

			StrCpy $5 $2 1
			IntOp $2 $2 + 0
			StrCmp${_WORDFUNC_S} $2 0 0 one
			StrCmp${_WORDFUNC_S} $5 0 error2
			StrCpy $3 ''

			all:
			StrCpy $5 0
			StrCpy $2 $R0 $7 $5
			StrCmp${_WORDFUNC_S} $2 '' +4
			StrCmp${_WORDFUNC_S} $2 $0 +6
			IntOp $5 $5 + 1
			goto -4
			StrCmp${_WORDFUNC_S} $R0 $R1 error1
			StrCpy $R0 '$3$R0'
			goto end
			StrCpy $2 $R0 $5
			IntOp $5 $5 + $7
			StrCmp${_WORDFUNC_S} $4 '*' 0 +3
			StrCpy $6 $R0 $7 $5
			StrCmp${_WORDFUNC_S} $6 $0 -3
			StrCpy $R0 $R0 '' $5
			StrCpy $3 '$3$2$1'
			goto all

			one:
			StrCpy $5 0
			StrCpy $8 0
			goto loop

			preloop:
			IntOp $5 $5 + 1

			loop:
			StrCpy $6 $R0 $7 $5
			StrCmp${_WORDFUNC_S} $6$8 0 error1
			StrCmp${_WORDFUNC_S} $6 '' minus
			StrCmp${_WORDFUNC_S} $6 $0 0 preloop
			IntOp $8 $8 + 1
			StrCmp${_WORDFUNC_S} $3$8 +$2 found
			IntOp $5 $5 + $7
			goto loop

			minus:
			StrCmp${_WORDFUNC_S} $3 '-' 0 error2
			StrCpy $3 +
			IntOp $2 $8 - $2
			IntOp $2 $2 + 1
			IntCmp $2 0 error2 error2 one

			found:
			StrCpy $3 $R0 $5
			StrCmp${_WORDFUNC_S} $4 '*' 0 +5
			StrCpy $6 $3 '' -$7
			StrCmp${_WORDFUNC_S} $6 $0 0 +3
			StrCpy $3 $3 -$7
			goto -3
			IntOp $5 $5 + $7
			StrCmp${_WORDFUNC_S} $4 '*' 0 +3
			StrCpy $6 $R0 $7 $5
			StrCmp${_WORDFUNC_S} $6 $0 -3
			StrCpy $R0 $R0 '' $5
			StrCpy $R0 '$3$1$R0'
			goto end

			error3:
			StrCpy $R0 3
			goto error
			error2:
			StrCpy $R0 2
			goto error
			error1:
			StrCpy $R0 1
			error:
			StrCmp $9 'E' +3
			StrCpy $R0 $R1
			goto +2
			SetErrors

			end:
			Pop $R1
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
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro WordAdd
	!ifndef ${_WORDFUNC_UN}WordAdd${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!insertmacro WordFind

		!define ${_WORDFUNC_UN}WordAdd${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordAdd${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordAdd${_WORDFUNC_S}
			Exch $1
			Exch
			Exch $0
			Exch
			Exch 2
			Exch $R0
			Exch 2
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $R1
			ClearErrors

			StrCpy $7 ''
			StrCpy $2 $1 1
			StrCmp $2 'E' 0 +4
			StrCpy $7 E
			StrCpy $1 $1 '' 1
			goto -4

			StrCpy $5 0
			StrCpy $R1 $R0
			StrCpy $2 $1 '' 1
			StrCpy $1 $1 1
			StrCmp${_WORDFUNC_S} $1 '+' +2
			StrCmp${_WORDFUNC_S} $1 '-' 0 error3

			StrCmp${_WORDFUNC_S} $0 '' error1
			StrCmp${_WORDFUNC_S} $2 '' end
			StrCmp${_WORDFUNC_S} $R0 '' 0 +5
			StrCmp${_WORDFUNC_S} $1 '-' end
			StrCmp${_WORDFUNC_S} $1 '+' 0 +3
			StrCpy $R0 $2
			goto end

			loop:
			IntOp $5 $5 + 1
			Push `$2`
			Push `$0`
			Push `E+$5`
			Call ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
			Pop $3
			IfErrors 0 /word
			StrCmp${_WORDFUNC_S} $3 2 +4
			StrCmp${_WORDFUNC_S} $3$5 11 0 +3
			StrCpy $3 $2
			goto /word
			StrCmp${_WORDFUNC_S} $1 '-' end preend

			/word:
			Push `$R0`
			Push `$0`
			Push `E/$3`
			Call ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
			Pop $4
			IfErrors +2
			StrCmp${_WORDFUNC_S} $1 '-' delete loop
			StrCmp${_WORDFUNC_S} $1$4 '-1' +2
			StrCmp${_WORDFUNC_S} $1 '-' loop +4
			StrCmp${_WORDFUNC_S} $R0 $3 0 loop
			StrCpy $R0 ''
			goto end
			StrCmp${_WORDFUNC_S} $1$4 '+1' 0 +2
			StrCmp${_WORDFUNC_S} $R0 $3 loop
			StrCmp${_WORDFUNC_S} $R0 $R1 +3
			StrCpy $R1 '$R1$0$3'
			goto loop
			StrLen $6 $0
			StrCpy $6 $R0 '' -$6
			StrCmp${_WORDFUNC_S} $6 $0 0 -4
			StrCpy $R1 '$R1$3'
			goto loop

			delete:
			Push `$R0`
			Push `$0`
			Push `E+$4{}`
			Call ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
			Pop $R0
			goto /word

			error3:
			StrCpy $R1 3
			goto error
			error1:
			StrCpy $R1 1
			error:
			StrCmp $7 'E' 0 end
			SetErrors

			preend:
			StrCpy $R0 $R1

			end:
			Pop $R1
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro WordInsert
	!ifndef ${_WORDFUNC_UN}WordInsert${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!insertmacro WordFind

		!define ${_WORDFUNC_UN}WordInsert${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}WordInsert${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}WordInsert${_WORDFUNC_S}
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Exch 3
			Exch $R0
			Exch 3
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $8
			Push $9
			Push $R1
			ClearErrors

			StrCpy $5 ''
			StrCpy $6 $0
			StrCpy $7 }

			StrCpy $9 ''
			StrCpy $R1 $R0
			StrCpy $3 $2 1
			StrCpy $2 $2 '' 1
			StrCmp $3 'E' 0 +3
			StrCpy $9 'E'
			goto -4

			StrCmp${_WORDFUNC_S} $3 '+' +2
			StrCmp${_WORDFUNC_S} $3 '-' 0 error3
			IntOp $2 $2 + 0
			StrCmp${_WORDFUNC_S} $2 0 error2
			StrCmp${_WORDFUNC_S} $0 '' error1

			StrCmp${_WORDFUNC_S} $2 1 0 two
			GetLabelAddress $8 oneback
			StrCmp${_WORDFUNC_S} $3 '+' call
			StrCpy $7 {
			goto call
			oneback:
			IfErrors 0 +2
			StrCpy $4 $R0
			StrCmp${_WORDFUNC_S} $3 '+' 0 +3
			StrCpy $R0 '$1$0$4'
			goto end
			StrCpy $R0 '$4$0$1'
			goto end

			two:
			IntOp $2 $2 - 1
			GetLabelAddress $8 twoback
			StrCmp${_WORDFUNC_S} $3 '+' 0 call
			StrCpy $7 {
			goto call
			twoback:
			IfErrors 0 tree
			StrCmp${_WORDFUNC_S} $2$4 11 0 error2
			StrCmp${_WORDFUNC_S} $3 '+' 0 +3
			StrCpy $R0 '$R0$0$1'
			goto end
			StrCpy $R0 '$1$0$R0'
			goto end

			tree:
			StrCpy $7 }
			StrCpy $5 $4
			IntOp $2 $2 + 1
			GetLabelAddress $8 treeback
			StrCmp${_WORDFUNC_S} $3 '+' call
			StrCpy $7 {
			goto call
			treeback:
			IfErrors 0 +3
			StrCpy $4 ''
			StrCpy $6 ''
			StrCmp${_WORDFUNC_S} $3 '+' 0 +3
			StrCpy $R0 '$5$0$1$6$4'
			goto end
			StrCpy $R0 '$4$6$1$0$5'
			goto end

			call:			
			Push '$R0'
			Push '$0'
			Push 'E$3$2*$7'
			Call ${_WORDFUNC_UN}WordFind${_WORDFUNC_S}
			Pop $4
			goto $8

			error3:
			StrCpy $R0 3
			goto error
			error2:
			StrCpy $R0 2
			goto error
			error1:
			StrCpy $R0 1
			error:
			StrCmp $9 'E' +3
			StrCpy $R0 $R1
			goto +2
			SetErrors

			end:
			Pop $R1
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
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro StrFilter
	!ifndef ${_WORDFUNC_UN}StrFilter${_WORDFUNC_S}
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}StrFilter${_WORDFUNC_S} `!insertmacro ${_WORDFUNC_UN}StrFilter${_WORDFUNC_S}Call`

		Function ${_WORDFUNC_UN}StrFilter${_WORDFUNC_S}
			Exch $2
			Exch
			Exch $1
			Exch
			Exch 2
			Exch $0
			Exch 2
			Exch 3
			Exch $R0
			Exch 3
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7
			Push $R1
			Push $R2
			Push $R3
			Push $R4
			Push $R5
			Push $R6
			Push $R7
			Push $R8
			ClearErrors

			StrCpy $R2 $0 '' -3
			StrCmp $R2 eng eng
			StrCmp $R2 rus rus
			eng:
			StrCpy $4 65
			StrCpy $5 90
			StrCpy $6 97
			StrCpy $7 122
			goto langend
			rus:
			StrCpy $4 192
			StrCpy $5 223
			StrCpy $6 224
			StrCpy $7 255
			goto langend
			;...

			langend:
			StrCpy $R7 ''
			StrCpy $R8 ''

			StrCmp${_WORDFUNC_S} $2 '' 0 begin

			restart1:
			StrCpy $2 ''
			StrCpy $3 $0 1
			StrCmp${_WORDFUNC_S} $3 '+' +2
			StrCmp${_WORDFUNC_S} $3 '-' 0 +3
			StrCpy $0 $0 '' 1
			goto +2
			StrCpy $3 ''

			IntOp $0 $0 + 0
			StrCmp${_WORDFUNC_S} $0 0 +5
			StrCpy $R7 $0 1 0
			StrCpy $R8 $0 1 1
			StrCpy $R2 $0 1 2
			StrCmp${_WORDFUNC_S} $R2 '' filter error

			restart2:
			StrCmp${_WORDFUNC_S} $3 '' end
			StrCpy $R7 ''
			StrCpy $R8 '+-'
			goto begin

			filter:
			StrCmp${_WORDFUNC_S} $R7 '1' +3
			StrCmp${_WORDFUNC_S} $R7 '2' +2
			StrCmp${_WORDFUNC_S} $R7 '3' 0 error

			StrCmp${_WORDFUNC_S} $R8 '' begin
			StrCmp${_WORDFUNC_S} $R7$R8 '23' +2
			StrCmp${_WORDFUNC_S} $R7$R8 '32' 0 +3
			StrCpy $R7 -1
			goto begin
			StrCmp${_WORDFUNC_S} $R7$R8 '13' +2
			StrCmp${_WORDFUNC_S} $R7$R8 '31' 0 +3
			StrCpy $R7 -2
			goto begin
			StrCmp${_WORDFUNC_S} $R7$R8 '12' +2
			StrCmp${_WORDFUNC_S} $R7$R8 '21' 0 error
			StrCpy $R7 -3

			begin:
			StrCpy $R6 0
			StrCpy $R1 ''

			loop:
			StrCpy $R2 $R0 1 $R6
			StrCmp${_WORDFUNC_S} $R2 '' restartchk

			StrCmp${_WORDFUNC_S} $2 '' +7
			StrCpy $R4 0
			StrCpy $R5 $2 1 $R4
			StrCmp${_WORDFUNC_S} $R5 '' addsymbol
			StrCmp${_WORDFUNC_S} $R5 $R2 skipsymbol
			IntOp $R4 $R4 + 1
			goto -4

			StrCmp${_WORDFUNC_S} $1 '' +7
			StrCpy $R4 0
			StrCpy $R5 $1 1 $R4
			StrCmp${_WORDFUNC_S} $R5 '' +4
			StrCmp${_WORDFUNC_S} $R5 $R2 addsymbol
			IntOp $R4 $R4 + 1
			goto -4

			StrCmp${_WORDFUNC_S} $R7 '1' +2
			StrCmp${_WORDFUNC_S} $R7 '-1' 0 +4
			StrCpy $R4 48
			StrCpy $R5 57
			goto loop2
			StrCmp${_WORDFUNC_S} $R8 '+-' 0 +2
			StrCmp${_WORDFUNC_S} $3 '+' 0 +4
			StrCpy $R4 $4
			StrCpy $R5 $5
			goto loop2
			StrCpy $R4 $6
			StrCpy $R5 $7

			loop2:
			IntFmt $R3 '%c' $R4
			StrCmp $R2 $R3 found
			StrCmp $R4 $R5 notfound
			IntOp $R4 $R4 + 1
			goto loop2

			found:
			StrCmp${_WORDFUNC_S} $R8 '+-' setcase
			StrCmp${_WORDFUNC_S} $R7 '3' skipsymbol
			StrCmp${_WORDFUNC_S} $R7 '-3' addsymbol
			StrCmp${_WORDFUNC_S} $R8 '' addsymbol skipsymbol

			notfound:
			StrCmp${_WORDFUNC_S} $R8 '+-' addsymbol
			StrCmp${_WORDFUNC_S} $R7 '3' 0 +2
			StrCmp${_WORDFUNC_S} $R5 57 addsymbol +3
			StrCmp${_WORDFUNC_S} $R7 '-3' 0 +5
			StrCmp${_WORDFUNC_S} $R5 57 skipsymbol
			StrCpy $R4 48
			StrCpy $R5 57
			goto loop2
			StrCmp${_WORDFUNC_S} $R8 '' skipsymbol addsymbol

			setcase:
			StrCpy $R2 $R3
			addsymbol:
			StrCpy $R1 $R1$R2
			skipsymbol:
			IntOp $R6 $R6 + 1
			goto loop

			error:
			SetErrors
			StrCpy $R0 ''
			goto end

			restartchk:
			StrCpy $R0 $R1
			StrCmp${_WORDFUNC_S} $2 '' 0 restart1
			StrCmp${_WORDFUNC_S} $R8 '+-' 0 restart2

			end:
			Pop $R8
			Pop $R7
			Pop $R6
			Pop $R5
			Pop $R4
			Pop $R3
			Pop $R2
			Pop $R1
			Pop $7
			Pop $6
			Pop $5
			Pop $4
			Pop $3
			Pop $2
			Pop $1
			Pop $0
			Exch $R0
		FunctionEnd

		!verbose pop
	!endif
!macroend

!macro VersionCompare
	!ifndef ${_WORDFUNC_UN}VersionCompare
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}VersionCompare `!insertmacro ${_WORDFUNC_UN}VersionCompareCall`

		Function ${_WORDFUNC_UN}VersionCompare
			Exch $1
			Exch
			Exch $0
			Exch
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7

			begin:
			StrCpy $2 -1
			IntOp $2 $2 + 1
			StrCpy $3 $0 1 $2
			StrCmp $3 '' +2
			StrCmp $3 '.' 0 -3
			StrCpy $4 $0 $2
			IntOp $2 $2 + 1
			StrCpy $0 $0 '' $2

			StrCpy $2 -1
			IntOp $2 $2 + 1
			StrCpy $3 $1 1 $2
			StrCmp $3 '' +2
			StrCmp $3 '.' 0 -3
			StrCpy $5 $1 $2
			IntOp $2 $2 + 1
			StrCpy $1 $1 '' $2

			StrCmp $4$5 '' equal

			StrCpy $6 -1
			IntOp $6 $6 + 1
			StrCpy $3 $4 1 $6
			StrCmp $3 '0' -2
			StrCmp $3 '' 0 +2
			StrCpy $4 0

			StrCpy $7 -1
			IntOp $7 $7 + 1
			StrCpy $3 $5 1 $7
			StrCmp $3 '0' -2
			StrCmp $3 '' 0 +2
			StrCpy $5 0

			StrCmp $4 0 0 +2
			StrCmp $5 0 begin newer2
			StrCmp $5 0 newer1
			IntCmp $6 $7 0 newer1 newer2

			StrCpy $4 '1$4'
			StrCpy $5 '1$5'
			IntCmp $4 $5 begin newer2 newer1

			equal:
			StrCpy $0 0
			goto end
			newer1:
			StrCpy $0 1
			goto end
			newer2:
			StrCpy $0 2

			end:
			Pop $7
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

!macro VersionConvert
	!ifndef ${_WORDFUNC_UN}VersionConvert
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!define ${_WORDFUNC_UN}VersionConvert `!insertmacro ${_WORDFUNC_UN}VersionConvertCall`

		Function ${_WORDFUNC_UN}VersionConvert
			Exch $1
			Exch
			Exch $0
			Exch
			Push $2
			Push $3
			Push $4
			Push $5
			Push $6
			Push $7

			StrCmp $1 '' 0 +2
			StrCpy $1 'abcdefghijklmnopqrstuvwxyz'
			StrCpy $1 $1 99

			StrCpy $2 0
			StrCpy $7 'dot'
			goto loop

			preloop:
			IntOp $2 $2 + 1

			loop:
			StrCpy $3 $0 1 $2
			StrCmp $3 '' endcheck
			StrCmp $3 '.' dot
			StrCmp $3 '0' digit
			IntCmp $3 '0' letter letter digit

			dot:
			StrCmp $7 'dot' replacespecial
			StrCpy $7 'dot'
			goto preloop

			digit:
			StrCmp $7 'letter' insertdot
			StrCpy $7 'digit'
			goto preloop

			letter:
			StrCpy $5 0
			StrCpy $4 $1 1 $5
			IntOp $5 $5 + 1
			StrCmp $4 '' replacespecial
			StrCmp $4 $3 0 -3
			IntCmp $5 9 0 0 +2
			StrCpy $5 '0$5'

			StrCmp $7 'letter' +2
			StrCmp $7 'dot' 0 +3
			StrCpy $6 ''
			goto +2
			StrCpy $6 '.'

			StrCpy $4 $0 $2
			IntOp $2 $2 + 1
			StrCpy $0 $0 '' $2
			StrCpy $0 '$4$6$5$0'
			StrLen $4 '$6$5'
			IntOp $2 $2 + $4
			IntOp $2 $2 - 1
			StrCpy $7 'letter'
			goto loop

			replacespecial:
			StrCmp $7 'dot' 0 +3
			StrCpy $6 ''
			goto +2
			StrCpy $6 '.'

			StrCpy $4 $0 $2
			IntOp $2 $2 + 1
			StrCpy $0 $0 '' $2
			StrCpy $0 '$4$6$0'
			StrLen $4 $6
			IntOp $2 $2 + $4
			IntOp $2 $2 - 1
			StrCpy $7 'dot'
			goto loop

			insertdot:
			StrCpy $4 $0 $2
			StrCpy $0 $0 '' $2
			StrCpy $0 '$4.$0'
			StrCpy $7 'dot'
			goto preloop

			endcheck:
			StrCpy $4 $0 1 -1
			StrCmp $4 '.' 0 end
			StrCpy $0 $0 -1
			goto -3

			end:
			Pop $7
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


# Uninstall. Case insensitive. #

!macro un.WordFindCall _STRING _DELIMITER _OPTION _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_OPTION}`
	Call un.WordFind
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordFind2XCall _STRING _DELIMITER1 _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call un.WordFind2X
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordFind3XCall _STRING _DELIMITER1 _CENTER _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_CENTER}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call un.WordFind3X
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordReplaceCall _STRING _WORD1 _WORD2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_WORD1}`
	Push `${_WORD2}`
	Push `${_NUMBER}`
	Call un.WordReplace
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordAddCall _STRING1 _DELIMITER _STRING2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING1}`
	Push `${_DELIMITER}`
	Push `${_STRING2}`
	Call un.WordAdd
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordInsertCall _STRING _DELIMITER _WORD _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_WORD}`
	Push `${_NUMBER}`
	Call un.WordInsert
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.StrFilterCall _STRING _FILTER _INCLUDE _EXCLUDE _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_FILTER}`
	Push `${_INCLUDE}`
	Push `${_EXCLUDE}`
	Call un.StrFilter
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.VersionCompareCall _VER1 _VER2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_VER1}`
	Push `${_VER2}`
	Call un.VersionCompare
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.VersionConvertCall _VERSION _CHARLIST _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_VERSION}`
	Push `${_CHARLIST}`
	Call un.VersionConvert
	Pop ${_RESULT}
	!verbose pop
!macroend


!macro un.WordFind
	!ifndef un.WordFind
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordFind

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.WordFind2X
	!ifndef un.WordFind2X
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordFind2X

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.WordFind3X
	!ifndef un.WordFind3X
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordFind3X

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.WordReplace
	!ifndef un.WordReplace
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordReplace

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.WordAdd
	!ifndef un.WordAdd
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordAdd

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.WordInsert
	!ifndef un.WordInsert
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro WordInsert

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.StrFilter
	!ifndef un.StrFilter
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro StrFilter

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.VersionCompare
	!ifndef un.VersionCompare
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro VersionCompare

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend

!macro un.VersionConvert
	!ifndef un.VersionConvert
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`

		!insertmacro VersionConvert

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!verbose pop
	!endif
!macroend


# Install. Case sensitive. #

!macro WordFindSCall _STRING _DELIMITER _OPTION _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_OPTION}`
	Call WordFindS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFind2XSCall _STRING _DELIMITER1 _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call WordFind2XS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFind3XSCall _STRING _DELIMITER1 _CENTER _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_CENTER}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call WordFind3XS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordReplaceSCall _STRING _WORD1 _WORD2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_WORD1}`
	Push `${_WORD2}`
	Push `${_NUMBER}`
	Call WordReplaceS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordAddSCall _STRING1 _DELIMITER _STRING2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING1}`
	Push `${_DELIMITER}`
	Push `${_STRING2}`
	Call WordAddS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordInsertSCall _STRING _DELIMITER _WORD _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_WORD}`
	Push `${_NUMBER}`
	Call WordInsertS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro StrFilterSCall _STRING _FILTER _INCLUDE _EXCLUDE _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_FILTER}`
	Push `${_INCLUDE}`
	Push `${_EXCLUDE}`
	Call StrFilterS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro WordFindS
	!ifndef WordFindS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordFind

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro WordFind2XS
	!ifndef WordFind2XS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordFind2X

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro WordFind3XS
	!ifndef WordFind3XS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordFind3X

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro WordReplaceS
	!ifndef WordReplaceS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordReplace

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro WordAddS
	!ifndef WordAddS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordAdd

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro WordInsertS
	!ifndef WordInsertS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordInsert

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro StrFilterS
	!ifndef StrFilterS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro StrFilter

		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend


# Uninstall. Case sensitive. #

!macro un.WordFindSCall _STRING _DELIMITER _OPTION _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_OPTION}`
	Call un.WordFindS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordFind2XSCall _STRING _DELIMITER1 _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call un.WordFind2XS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordFind3XSCall _STRING _DELIMITER1 _CENTER _DELIMITER2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER1}`
	Push `${_CENTER}`
	Push `${_DELIMITER2}`
	Push `${_NUMBER}`
	Call un.WordFind3XS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordReplaceSCall _STRING _WORD1 _WORD2 _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_WORD1}`
	Push `${_WORD2}`
	Push `${_NUMBER}`
	Call un.WordReplaceS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordAddSCall _STRING1 _DELIMITER _STRING2 _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING1}`
	Push `${_DELIMITER}`
	Push `${_STRING2}`
	Call un.WordAddS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordInsertSCall _STRING _DELIMITER _WORD _NUMBER _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_DELIMITER}`
	Push `${_WORD}`
	Push `${_NUMBER}`
	Call un.WordInsertS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.StrFilterSCall _STRING _FILTER _INCLUDE _EXCLUDE _RESULT
	!verbose push
	!verbose ${_WORDFUNC_VERBOSE}
	Push `${_STRING}`
	Push `${_FILTER}`
	Push `${_INCLUDE}`
	Push `${_EXCLUDE}`
	Call un.StrFilterS
	Pop ${_RESULT}
	!verbose pop
!macroend

!macro un.WordFindS
	!ifndef un.WordFindS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_S
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!define _WORDFUNC_S `S`

		!insertmacro WordFind

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.WordFind2XS
	!ifndef un.WordFind2XS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordFind2X

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.WordFind3XS
	!ifndef un.WordFind3XS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordFind3X

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.WordReplaceS
	!ifndef un.WordReplaceS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordReplace

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.WordAddS
	!ifndef un.WordAddS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordAdd

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.WordInsertS
	!ifndef un.WordInsertS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro WordInsert

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!macro un.StrFilterS
	!ifndef un.StrFilterS
		!verbose push
		!verbose ${_WORDFUNC_VERBOSE}
		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN `un.`
		!undef _WORDFUNC_S
		!define _WORDFUNC_S `S`

		!insertmacro StrFilter

		!undef _WORDFUNC_UN
		!define _WORDFUNC_UN
		!undef _WORDFUNC_S
		!define _WORDFUNC_S
		!verbose pop
	!endif
!macroend

!endif
