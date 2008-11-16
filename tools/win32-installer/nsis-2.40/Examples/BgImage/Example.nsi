Name "BgImage.dll test"

OutFile "BgImage Test.exe"

XPStyle on

!define DEBUG
!macro GetReturnValue
!ifdef DEBUG
	Pop $R9
	StrCmp $R9 success +2
		DetailPrint "Error: $R9"
!endif
!macroend

Function .onGUIInit
	# the plugins dir is automatically deleted when the installer exits
	InitPluginsDir
	# lets extract some bitmaps...
	File /oname=$PLUGINSDIR\1.bmp "${NSISDIR}\Contrib\Graphics\Wizard\llama.bmp"
	File /oname=$PLUGINSDIR\2.bmp "${NSISDIR}\Contrib\Graphics\Checks\modern.bmp"

!ifdef DEBUG
	# turn return values on if in debug mode
	BgImage::SetReturn /NOUNLOAD on
!endif

	# set the initial background for images to be drawn on
	# we will use a gradient from drak green to dark red
	BgImage::SetBg /NOUNLOAD /GRADIENT 0 0x80 0 0x80 0 0
	!insertmacro GetReturnValue
	# add an image @ (150,0)
	BgImage::AddImage /NOUNLOAD $PLUGINSDIR\2.bmp 150 0
	!insertmacro GetReturnValue
	# add the same image only transparent (magenta wiped) @ (150,16)
	BgImage::AddImage /NOUNLOAD /TRANSPARENT 255 0 255 $PLUGINSDIR\2.bmp 150 16
	!insertmacro GetReturnValue
	# create the font for the following text
	CreateFont $R0 "Comic Sans MS" 50 700
	# add a blue shadow for the text
	BgImage::AddText /NOUNLOAD "Testing 1... 2... 3..." $R0 0 0 255 48 48 798 198
	!insertmacro GetReturnValue
	# add a green shadow for the text
	BgImage::AddText /NOUNLOAD "Testing 1... 2... 3..." $R0 0 255 0 52 52 802 202
	!insertmacro GetReturnValue
	# add the text
	BgImage::AddText /NOUNLOAD "Testing 1... 2... 3..." $R0 255 0 0 50 50 800 200
	!insertmacro GetReturnValue
	# show our creation to the world!
	BgImage::Redraw /NOUNLOAD
	# Refresh doesn't return any value
	
FunctionEnd

ShowInstDetails show

Section
	# play some sounds
	FindFirst $0 $1 $WINDIR\Media\*.wav
	StrCmp $0 "" skipSound
		moreSounds:
		StrCmp $1 "" noMoreSounds
			BgImage::Sound /NOUNLOAD /WAIT $WINDIR\Media\$1
			# Sound doesn't return any value either
			MessageBox MB_YESNO "Another sound?" IDNO noMoreSounds
				FindNext $0 $1
				Goto moreSounds

	noMoreSounds:
		FindClose $0
	skipSound:

	# change the background image to Mike, tiled
	BgImage::SetBg /NOUNLOAD /TILED $PLUGINSDIR\1.bmp
	!insertmacro GetReturnValue
	# we have to redraw to reflect the changes
	BgImage::Redraw /NOUNLOAD

	MessageBox MB_OK "Mike the llama"

	# clear everything
	BgImage::Clear /NOUNLOAD
	# Clear doesn't return any value
	# set another gradient
	BgImage::SetBg /NOUNLOAD /GRADIENT 0xFF 0xFA 0xBA 0xAA 0xA5 0x65
	!insertmacro GetReturnValue
	# add some text
	BgImage::AddText /NOUNLOAD "A Desert for Mike" $R0 0 0 0 50 50 800 150
	!insertmacro GetReturnValue
	# add mike as an image
	BgImage::AddImage /NOUNLOAD $PLUGINSDIR\1.bmp 50 150
	!insertmacro GetReturnValue
	# again, we have to call redraw to reflect changes
	BgImage::Redraw /NOUNLOAD
SectionEnd

Function .onGUIEnd
	# Destroy must not have /NOUNLOAD so NSIS will be able to unload
	# and delete BgImage before it exits
	BgImage::Destroy
	# Destroy doesn't return any value
FunctionEnd