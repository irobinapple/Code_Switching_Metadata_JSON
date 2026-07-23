'=====================================================================
' CODE-SWITCHING PROJECT - MASTER METADATA WORKBOOK MACROS  (v9)
'=====================================================================
' v9 changes vs v8:
'   1. Secondary (English) language code: client reversed the earlier rule.
'      It is now bare "en" for every locale EXCEPT the Indian ones
'      (Hindi & Tamil), which stay "en_IN". Applied everywhere the code is
'      emitted - spokenLanguages, each speaker's languages, and
'      segmentLanguages - via the new NormalizeSecondaryEnglish() helper, so
'      en_VN / en_BR / en_US / ... all become "en" while en_IN is preserved.
'   2. speakers array order now lists any "No-Speaker" FIRST, then the real
'      speakers (matching the client file). Built in two passes.
'
' v8 changes vs v7, to match the client's V1 JSON sample:
'   1. transcriptionData key "Transliteration" -> "transliteration"
'      (lowercase t) in every segment.
'   2. speakers[].languages: real speakers now list BOTH the primary and
'      secondary language codes (e.g. ["hi_IN", "en_IN"]); a "No-Speaker"
'      lists none ([]). Previously this was primary-only.
'   3. "No-Speaker" speakers now emit gender / speaker_age / speakerNativity
'      as "NA" (a No-Speaker segment - hold music / noise - has none of
'      these). Their *Source fields stay "Annotator", same as before.
'   4. JSON key order now mirrors the client's V1 file exactly at every level
'      (value -> languages, languageInfo, domainInfo, conventionInfo,
'      annotatorInfo, speakers, segments, taskStatus; segment ends with
'      segmentId then speakerId; speaker order gender, speaker_age, ...).
'      Purely cosmetic - JSON is order-independent - but makes our output
'      diff-identical to the client sample.
'   (speakerDominantVarieties was already the array-of-object form in v7 -
'    it already matches the V1 sample, so no change was needed there.)
'
' v7 change vs v6:
'   domainInfo.domainList is now wrapped in a JSON array containing one
'   object - [{"domain": "Call-center", "topicList": [...]}] - matching
'   the official client schema exactly. v6 and earlier incorrectly
'   output this as a bare object (not array-wrapped). This affected
'   every JSON generated so far (Conv0347, Conv0592, Conv0597) -
'   regenerated/repatched copies of those three are provided alongside
'   this macro update.
'
' v6 change vs v5:
'   Metadata CSV filename now uses the conversation's ConvID instead
'   of a timestamp, e.g. "Metadata_Export_20260721_Conv0597.csv"
'   instead of "Metadata_Export_20260721_024723.csv". If raw_metadata
'   happens to contain more than one ConvID at export time, the file
'   is named "..._Multi.csv" instead, since a single ConvID label
'   wouldn't be accurate.
'
' v5 changes vs v4:
'   1. Number_of_Turns in 'metadata' now counts turns PER SPEAKER
'      (e.g. Agent=62, Customer=58), not the whole conversation's
'      total duplicated onto every speaker row (was showing 120/120).
'   2. Duration_Sec and Number_of_Turns cells are now explicitly
'      forced to plain Number format every time they're written, so
'      they can't silently drift into a time/other format again.
'
' v4 change vs v3:
'   Start_Time_Sec / End_Time_Sec now support pasting the EXACT
'   timestamp text straight from the transcript - no manual math
'   needed. All of these work in the same column:
'     "00:01:23,500"   (SRT format, comma decimal - copy-paste as-is)
'     "1:23.5"          (M:SS.mmm)
'     "83.5"            (plain seconds - still works, unchanged)
'   This requires the raw_metadata Start_Time_Sec/End_Time_Sec columns
'   to be formatted as TEXT ("@") so Excel never tries to auto-convert
'   a pasted timestamp into its own time serial. The companion fixed
'   workbook (Gen4) already has this applied across the full sheet.
'
' v3 changes vs v2, per client feedback (confirmed):
'   1. Start/End timestamps: now converted correctly regardless of
'      whether the cell is time-formatted (h:mm:ss) or a plain number -
'      fixes the "start": 0.0000462... bug. New helper: CellSeconds().
'   2. value.languages -> only the primary language (was [primary, secondary]).
'   3. speakerDominantVarieties -> only the primary language entry.
'   4. domainInfo.domain -> hardcoded "Call-center".
'   5. domainInfo.topicList -> the abbreviated domain code from
'      raw_metadata's Domain column (AIR, BANK, FIN, INS, HEALTH, IT,
'      ECOM, TECHSUPPORT, BILLING, PRODUCT, ACCOUNT).
'   6. Language codes normalized: hyphens -> underscores everywhere
'      (e.g. "vi-VN" -> "vi_VN") as a safety net, wherever the macro
'      builds language arrays.
'   8. genderSource / speakerNativitySource -> always "Annotator".
'      speakerRoleSource -> "" for real speakers, "Annotator" only for
'      a "No-Speaker" role. (These 3 are now COMPUTED, not read from
'      the raw_metadata Speaker_*_Source columns - those columns can
'      stay in the sheet for your own notes, they're just no longer
'      used for JSON output.)
'   9. JSON key "transliteration" -> "Transliteration" (capital T).
'   New: "No-Speaker" is a valid Speaker_Role value for hold-music /
'      noise / pause segments. Add these as ordinary rows in
'      raw_metadata when needed - nothing auto-inserted.
'
' HOW TO INSTALL:
'   1. Open the workbook, Alt+F11
'   2. Select all existing macro code in the module, delete it
'   3. Paste this v9 code in
'   4. Close the VBA editor, save
'
' ALSO DO THIS ONCE IN THE SHEET (not code, just data/format):
'   - raw_metadata Domain column: make sure values use the short codes
'     (AIR, BANK, FIN, INS, HEALTH, IT, ECOM, TECHSUPPORT, BILLING,
'     PRODUCT, ACCOUNT) not full words like "AIRLINE".
'   - Primary_Language_Code: underscore format (vi_VN), not hyphens (vi-VN).
'   - Secondary_Language_Code / Speaker_Languages / Segment_Languages: the
'     English code is now bare "en" for every locale EXCEPT Indian ones
'     (Hindi/Tamil = "en_IN"). You may still leave old region-paired values
'     like "en_VN" in the sheet - v9 auto-collapses them to "en" on export
'     (and keeps "en_IN"), so either is safe.
'   - Speaker_Role dropdown: now also accepts "No-Speaker".
'=====================================================================

Option Explicit

Const COL_CONVID As Integer = 1
Const COL_LANGPAIR As Integer = 2
Const COL_PRIMARYLANG As Integer = 3
Const COL_SECONDARYLANG As Integer = 4
Const COL_DOMAIN As Integer = 5
Const COL_SAMPLINGRATE As Integer = 6
Const COL_RECDATE As Integer = 7
Const COL_SCRIPTPATH As Integer = 8
Const COL_AUDIOPATH As Integer = 9
Const COL_CONVENTION As Integer = 10
Const COL_ADDENDUM As Integer = 11
Const COL_ANNOTATOR As Integer = 12
Const COL_CSRATIO_P As Integer = 13
Const COL_CSRATIO_S As Integer = 14
Const COL_SPEAKERID As Integer = 15
Const COL_SPKROLE As Integer = 16
Const COL_SPKROLESRC As Integer = 17
Const COL_SPKGENDER As Integer = 18
Const COL_SPKGENDERSRC As Integer = 19
Const COL_SPKAGE As Integer = 20
Const COL_SPKNATIVITY As Integer = 21
Const COL_SPKNATIVITYSRC As Integer = 22
Const COL_SPKLANGS As Integer = 23
Const COL_TURNNO As Integer = 24
Const COL_SEGID As Integer = 25
Const COL_START As Integer = 26
Const COL_END As Integer = 27
Const COL_PRIMARYTYPE As Integer = 28
Const COL_LOUDNESS As Integer = 29
Const COL_SEGLANG As Integer = 30
Const COL_SEGLANGS As Integer = 31
Const COL_CONTENT As Integer = 32
Const COL_TRANSLIT As Integer = 33
Const COL_QCNOTES As Integer = 34

'=====================================================================
' MACRO 1: Build 'metadata' and 'JSON_data' from 'raw_metadata'
'=====================================================================
Sub BuildMetadataAndJSON()

    Dim wsRaw As Worksheet, wsMeta As Worksheet, wsJson As Worksheet
    Set wsRaw = ThisWorkbook.Sheets("raw_metadata")
    Set wsMeta = ThisWorkbook.Sheets("metadata")
    Set wsJson = ThisWorkbook.Sheets("JSON_data")

    Dim lastRow As Long
    lastRow = wsRaw.Cells(wsRaw.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then
        MsgBox "No data found in raw_metadata.", vbExclamation
        Exit Sub
    End If

    wsMeta.Rows("2:" & wsMeta.Rows.Count).ClearContents
    wsJson.Rows("2:" & wsJson.Rows.Count).ClearContents

    Dim dictConvTurns As Object, dictConvMinStart As Object, dictConvMaxEnd As Object
    Dim dictSpeakerTurns As Object
    Set dictConvTurns = CreateObject("Scripting.Dictionary")
    Set dictConvMinStart = CreateObject("Scripting.Dictionary")
    Set dictConvMaxEnd = CreateObject("Scripting.Dictionary")
    Set dictSpeakerTurns = CreateObject("Scripting.Dictionary")   ' keyed "ConvID|SpeakerID"

    Dim i As Long, convID As String, secs As Double

    For i = 2 To lastRow
        convID = Trim(CStr(wsRaw.Cells(i, COL_CONVID).Value))
        If convID <> "" And LCase(convID) <> "example" Then
            If Not dictConvTurns.Exists(convID) Then
                dictConvTurns(convID) = 0
                dictConvMinStart(convID) = 999999999#
                dictConvMaxEnd(convID) = 0#
            End If
            dictConvTurns(convID) = dictConvTurns(convID) + 1

            Dim spkKey As String
            spkKey = convID & "|" & Trim(CStr(wsRaw.Cells(i, COL_SPEAKERID).Value))
            If Not dictSpeakerTurns.Exists(spkKey) Then dictSpeakerTurns(spkKey) = 0
            dictSpeakerTurns(spkKey) = dictSpeakerTurns(spkKey) + 1

            secs = CellSeconds(wsRaw.Cells(i, COL_START))
            If secs < dictConvMinStart(convID) Then dictConvMinStart(convID) = secs
            secs = CellSeconds(wsRaw.Cells(i, COL_END))
            If secs > dictConvMaxEnd(convID) Then dictConvMaxEnd(convID) = secs
        End If
    Next i

    Dim dictSpeakerSeen As Object
    Set dictSpeakerSeen = CreateObject("Scripting.Dictionary")

    Dim metaRow As Long: metaRow = 2
    Dim jsonRow As Long: jsonRow = 2
    Dim sno As Long: sno = 1

    For i = 2 To lastRow
        convID = Trim(CStr(wsRaw.Cells(i, COL_CONVID).Value))
        If convID = "" Or LCase(convID) = "example" Then GoTo ContinueLoop

        Dim spkID As String, spkRole As String
        spkID = Trim(CStr(wsRaw.Cells(i, COL_SPEAKERID).Value))
        spkRole = Trim(CStr(wsRaw.Cells(i, COL_SPKROLE).Value))
        Dim key As String
        key = convID & "|" & spkID

        If Not dictSpeakerSeen.Exists(key) Then
            dictSpeakerSeen(key) = True

            Dim langPair As String, domain As String, sampRate As String, fileName As String
            langPair = wsRaw.Cells(i, COL_LANGPAIR).Value
            domain = NormalizeDomain(wsRaw.Cells(i, COL_DOMAIN).Value)
            sampRate = wsRaw.Cells(i, COL_SAMPLINGRATE).Value
            fileName = langPair & "_" & domain & "_" & sampRate & "_" & convID

            Dim durationSec As Double
            durationSec = dictConvMaxEnd(convID) - dictConvMinStart(convID)
            If durationSec < 0 Then durationSec = 0

            Dim roleSourceOut As String
            roleSourceOut = IIf(spkRole = "No-Speaker", "Annotator", "")

            wsMeta.Cells(metaRow, 1).Value = sno
            wsMeta.Cells(metaRow, 2).Value = fileName
            wsMeta.Cells(metaRow, 3).Value = convID
            wsMeta.Cells(metaRow, 4).Value = langPair
            wsMeta.Cells(metaRow, 5).Value = spkID
            wsMeta.Cells(metaRow, 6).Value = spkRole
            wsMeta.Cells(metaRow, 7).Value = roleSourceOut
            wsMeta.Cells(metaRow, 8).Value = wsRaw.Cells(i, COL_SPKGENDER).Value
            wsMeta.Cells(metaRow, 9).Value = "Annotator"
            wsMeta.Cells(metaRow, 10).Value = wsRaw.Cells(i, COL_SPKAGE).Value
            wsMeta.Cells(metaRow, 11).Value = wsRaw.Cells(i, COL_SPKNATIVITY).Value
            wsMeta.Cells(metaRow, 12).Value = "Annotator"
            wsMeta.Cells(metaRow, 13).Value = domain
            wsMeta.Cells(metaRow, 14).Value = durationSec
            wsMeta.Cells(metaRow, 14).NumberFormat = "0.00"          ' force plain seconds, never time
            wsMeta.Cells(metaRow, 15).Value = dictSpeakerTurns(key)   ' per-speaker turn count, not conversation total
            wsMeta.Cells(metaRow, 15).NumberFormat = "0"
            wsMeta.Cells(metaRow, 16).Value = sampRate
            wsMeta.Cells(metaRow, 17).Value = wsRaw.Cells(i, COL_CSRATIO_P).Value
            wsMeta.Cells(metaRow, 18).Value = wsRaw.Cells(i, COL_CSRATIO_S).Value
            wsMeta.Cells(metaRow, 19).Value = wsRaw.Cells(i, COL_RECDATE).Value
            wsMeta.Cells(metaRow, 20).Value = wsRaw.Cells(i, COL_SCRIPTPATH).Value
            wsMeta.Cells(metaRow, 21).Value = wsRaw.Cells(i, COL_AUDIOPATH).Value

            metaRow = metaRow + 1
            sno = sno + 1
        End If

        wsJson.Cells(jsonRow, 1).Value = convID
        wsJson.Cells(jsonRow, 2).Value = wsRaw.Cells(i, COL_SEGID).Value
        wsJson.Cells(jsonRow, 3).Value = spkID
        wsJson.Cells(jsonRow, 4).Value = CellSeconds(wsRaw.Cells(i, COL_START))
        wsJson.Cells(jsonRow, 5).Value = CellSeconds(wsRaw.Cells(i, COL_END))
        wsJson.Cells(jsonRow, 6).Value = wsRaw.Cells(i, COL_PRIMARYTYPE).Value
        wsJson.Cells(jsonRow, 7).Value = wsRaw.Cells(i, COL_LOUDNESS).Value
        wsJson.Cells(jsonRow, 8).Value = NormalizeLangCode(wsRaw.Cells(i, COL_SEGLANG).Value)
        wsJson.Cells(jsonRow, 9).Value = wsRaw.Cells(i, COL_SEGLANGS).Value
        wsJson.Cells(jsonRow, 10).Value = wsRaw.Cells(i, COL_CONTENT).Value
        wsJson.Cells(jsonRow, 11).Value = wsRaw.Cells(i, COL_TRANSLIT).Value
        jsonRow = jsonRow + 1

ContinueLoop:
    Next i

    MsgBox "Done." & vbCrLf & _
           "metadata rows written: " & (metaRow - 2) & vbCrLf & _
           "JSON_data (segment) rows written: " & (jsonRow - 2), vbInformation
End Sub

'=====================================================================
' MACRO 2: Export consolidated metadata CSV + one JSON file per ConvID
'=====================================================================
Sub ExportMetadataAndJSONFiles()

    Dim outFolder As String
    outFolder = PickFolder("Select the offline output folder")
    If outFolder = "" Then Exit Sub
    If Right(outFolder, 1) <> "\" Then outFolder = outFolder & "\"

    Dim wsRaw As Worksheet, wsMeta As Worksheet, wsJson As Worksheet
    Set wsRaw = ThisWorkbook.Sheets("raw_metadata")
    Set wsMeta = ThisWorkbook.Sheets("metadata")
    Set wsJson = ThisWorkbook.Sheets("JSON_data")

    Dim metaLastRow As Long
    metaLastRow = wsMeta.Cells(wsMeta.Rows.Count, "A").End(xlUp).Row
    If metaLastRow < 2 Then
        MsgBox "'metadata' sheet is empty - run BuildMetadataAndJSON first.", vbExclamation
        Exit Sub
    End If

    ' Figure out the ConvID(s) currently in raw_metadata, for the filename
    Dim rawLastRow2 As Long, i2 As Long, convLabel As String
    Dim dictConvForName As Object
    Set dictConvForName = CreateObject("Scripting.Dictionary")
    rawLastRow2 = wsRaw.Cells(wsRaw.Rows.Count, "A").End(xlUp).Row
    For i2 = 2 To rawLastRow2
        Dim c2 As String
        c2 = Trim(CStr(wsRaw.Cells(i2, COL_CONVID).Value))
        If c2 <> "" And LCase(c2) <> "example" Then
            If Not dictConvForName.Exists(c2) Then dictConvForName.Add c2, True
        End If
    Next i2

    If dictConvForName.Count = 1 Then
        Dim onlyKey As Variant
        For Each onlyKey In dictConvForName.Keys
            convLabel = CStr(onlyKey)
        Next onlyKey
    Else
        convLabel = "Multi"   ' more than one ConvID currently in raw_metadata
    End If

    Dim metaCSVPath As String
    metaCSVPath = outFolder & "Metadata_Export_" & Format(Now, "yyyymmdd") & "_" & convLabel & ".csv"
    ExportRangeToCSV wsMeta, 1, metaLastRow, metaCSVPath

    Dim rawLastRow As Long
    rawLastRow = wsRaw.Cells(wsRaw.Rows.Count, "A").End(xlUp).Row

    Dim dictConv As Object
    Set dictConv = CreateObject("Scripting.Dictionary")
    Dim i As Long, convID As String
    For i = 2 To rawLastRow
        convID = Trim(CStr(wsRaw.Cells(i, COL_CONVID).Value))
        If convID <> "" And LCase(convID) <> "example" Then
            If Not dictConv.Exists(convID) Then dictConv.Add convID, True
        End If
    Next i

    If dictConv.Count = 0 Then
        MsgBox "No conversations found in raw_metadata.", vbExclamation
        Exit Sub
    End If

    Dim key As Variant
    Dim countFiles As Long: countFiles = 0
    For Each key In dictConv.Keys
        Dim jsonText As String
        jsonText = BuildConversationJSON(CStr(key), wsRaw, wsMeta, wsJson)

        Dim fname As String
        fname = GetFileNameForConv(CStr(key), wsRaw) & ".json"

        WriteUTF8File outFolder & fname, jsonText
        countFiles = countFiles + 1
    Next key

    MsgBox "Export complete." & vbCrLf & _
           "Metadata CSV: " & metaCSVPath & vbCrLf & _
           "JSON files written: " & countFiles & vbCrLf & _
           "Folder: " & outFolder, vbInformation
End Sub

Sub RunFullPipeline()
    BuildMetadataAndJSON
    ExportMetadataAndJSONFiles
End Sub

'=====================================================================
' HELPER FUNCTIONS
'=====================================================================

' Converts a raw_metadata Start/End cell to real elapsed seconds,
' regardless of whether the cell is time-formatted (h:mm:ss - Excel
' stores these as a fraction of a 24h day) or a plain number already
' in seconds. This is the fix for the "start": 0.0000462... bug.
Function CellSeconds(cell As Range) As Double
    Dim v As Variant
    v = cell.Value

    If IsEmpty(v) Or Trim(CStr(v)) = "" Then
        CellSeconds = 0
        Exit Function
    End If

    ' Text cell (recommended going forward): associates paste the exact
    ' timestamp from the transcript, e.g. "00:01:23,500" or "1:23.5" or
    ' plain "83.5" - all handled by ParseTimeToSeconds.
    If VarType(v) = vbString Then
        CellSeconds = ParseTimeToSeconds(CStr(v))
        Exit Function
    End If

    ' Numeric cell: could be a plain number already in seconds, or a
    ' legacy Excel time-of-day value (fraction of a 24h day) if the cell
    ' is still time-formatted from older data entry.
    If IsNumeric(v) Then
        Dim nf As String
        nf = LCase(cell.NumberFormat)
        If InStr(nf, "h") > 0 Or InStr(nf, ":") > 0 Or InStr(nf, "am/pm") > 0 Then
            CellSeconds = CDbl(v) * 86400   ' legacy time-serial fallback
        Else
            CellSeconds = CDbl(v)            ' already plain seconds
        End If
        Exit Function
    End If

    CellSeconds = 0
End Function

' Parses a timestamp typed or pasted as TEXT into total seconds.
' Accepts, in any of these forms:
'   "83.5"                  -> 83.5   (plain seconds)
'   "1:23.5"                -> 83.5   (M:SS.mmm)
'   "01:23.500"             -> 83.5   (MM:SS.mmm)
'   "00:01:23,500"          -> 83.5   (HH:MM:SS,mmm - exact SRT/transcript format,
'                                       comma or dot both work as the decimal separator)
Function ParseTimeToSeconds(raw As String) As Double
    Dim s As String
    s = Trim(raw)
    If s = "" Then
        ParseTimeToSeconds = 0
        Exit Function
    End If

    ' Normalize a comma decimal (SRT style) to a dot - but only replace
    ' the LAST comma, since colons already separate h/m/s.
    Dim lastComma As Long
    lastComma = InStrRev(s, ",")
    If lastComma > 0 Then
        s = Left(s, lastComma - 1) & "." & Mid(s, lastComma + 1)
    End If

    If InStr(s, ":") = 0 Then
        ' No colon at all -> plain seconds, e.g. "83.5"
        If IsNumeric(s) Then
            ParseTimeToSeconds = CDbl(s)
        Else
            ParseTimeToSeconds = 0
        End If
        Exit Function
    End If

    Dim parts() As String
    parts = Split(s, ":")

    Dim h As Double, m As Double, sec As Double
    Select Case UBound(parts)
        Case 2 ' HH:MM:SS(.mmm)
            h = Val(parts(0))
            m = Val(parts(1))
            sec = Val(parts(2))
        Case 1 ' MM:SS(.mmm) or M:SS.mmm
            h = 0
            m = Val(parts(0))
            sec = Val(parts(1))
        Case Else
            h = 0: m = 0: sec = 0
    End Select

    ParseTimeToSeconds = h * 3600 + m * 60 + sec
End Function

' Hyphen -> underscore normalization for language codes (vi-VN -> vi_VN)
Function NormalizeLangCode(code As Variant) As String
    NormalizeLangCode = Replace(CStr(code), "-", "_")
End Function

' v9: client rule for the SECONDARY (English) code - collapse any region-paired
' English (en_VN, en_BR, en_US, ...) to bare "en", EXCEPT the Indian pairing
' "en_IN" (Hindi / Tamil), which is kept as-is. Non-English codes pass through.
Function NormalizeSecondaryEnglish(code As Variant) As String
    Dim c As String
    c = NormalizeLangCode(Trim(CStr(code)))
    If LCase(Left(c, 3)) = "en_" And LCase(c) <> "en_in" Then
        NormalizeSecondaryEnglish = "en"
    Else
        NormalizeSecondaryEnglish = c
    End If
End Function

' Upper-cases and trims a Domain value (AIR, BANK, FIN, INS, HEALTH,
' IT, ECOM, TECHSUPPORT, BILLING, PRODUCT, ACCOUNT expected)
Function NormalizeDomain(dom As Variant) As String
    NormalizeDomain = UCase(Trim(CStr(dom)))
End Function

Function PickFolder(promptTitle As String) As String
    Dim fd As FileDialog
    Set fd = Application.FileDialog(msoFileDialogFolderPicker)
    fd.Title = promptTitle
    If fd.Show = -1 Then
        PickFolder = fd.SelectedItems(1)
    Else
        PickFolder = ""
    End If
End Function

Function GetFileNameForConv(convID As String, wsRaw As Worksheet) As String
    Dim lastRow As Long, i As Long
    lastRow = wsRaw.Cells(wsRaw.Rows.Count, "A").End(xlUp).Row
    For i = 2 To lastRow
        If Trim(CStr(wsRaw.Cells(i, COL_CONVID).Value)) = convID Then
            Dim result As String
            result = wsRaw.Cells(i, COL_LANGPAIR).Value & "_"
            result = result & NormalizeDomain(wsRaw.Cells(i, COL_DOMAIN).Value) & "_"
            result = result & wsRaw.Cells(i, COL_SAMPLINGRATE).Value & "_" & convID
            GetFileNameForConv = result
            Exit Function
        End If
    Next i
    GetFileNameForConv = convID
End Function

Function JSONEscape(s As Variant) As String
    Dim r As String
    r = CStr(s)
    r = Replace(r, "\", "\\")
    r = Replace(r, """", "\""")
    r = Replace(r, vbCrLf, "\n")
    r = Replace(r, vbCr, "\n")
    r = Replace(r, vbLf, "\n")
    r = Replace(r, vbTab, "\t")
    JSONEscape = r
End Function

Function CSVListToJSONArray(csv As Variant) As String
    Dim s As String
    s = Trim(CStr(csv))
    If s = "" Then
        CSVListToJSONArray = "[]"
        Exit Function
    End If
    Dim parts() As String
    parts = Split(s, ",")
    Dim items() As String
    ReDim items(LBound(parts) To UBound(parts))
    Dim i As Long
    For i = LBound(parts) To UBound(parts)
        ' v9: normalize the secondary English code (en_VN -> en, en_IN kept).
        items(i) = """" & JSONEscape(NormalizeSecondaryEnglish(Trim(parts(i)))) & """"
    Next i
    CSVListToJSONArray = "[" & Join(items, ", ") & "]"
End Function

Function FormatNum(v As Variant) As String
    If IsNumeric(v) Then
        FormatNum = Replace(CStr(CDbl(v)), ",", ".")
    Else
        FormatNum = "0"
    End If
End Function

Sub WriteUTF8File(filePath As String, content As String)
    Dim ts As Object
    Set ts = CreateObject("ADODB.Stream")
    ts.Type = 2
    ts.Charset = "utf-8"
    ts.Open
    ts.WriteText content
    ts.Position = 0
    ts.Type = 1
    ts.Position = 3
    Dim raw() As Byte
    raw = ts.Read
    ts.Close

    Dim outStream As Object
    Set outStream = CreateObject("ADODB.Stream")
    outStream.Type = 1
    outStream.Open
    outStream.Write raw
    outStream.SaveToFile filePath, 2
    outStream.Close
End Sub

Sub ExportRangeToCSV(ws As Worksheet, headerRow As Long, lastRow As Long, filePath As String)
    Dim lastCol As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column

    Dim sb As String
    Dim r As Long, c As Long
    For r = headerRow To lastRow
        Dim lineArr() As String
        ReDim lineArr(1 To lastCol)
        For c = 1 To lastCol
            Dim v As String
            v = CStr(ws.Cells(r, c).Value)
            v = Replace(v, """", """""")
            If InStr(v, ",") > 0 Or InStr(v, vbCr) > 0 Or InStr(v, vbLf) > 0 Or InStr(v, """") > 0 Then
                v = """" & v & """"
            End If
            lineArr(c) = v
        Next c
        sb = sb & Join(lineArr, ",") & vbCrLf
    Next r

    WriteUTF8File filePath, sb
End Sub

Sub AddLine(ByRef target As String, ByVal line As String)
    target = target & line & vbCrLf
End Sub

' Builds the full nested JSON text for one conversation.
Function BuildConversationJSON(convID As String, wsRaw As Worksheet, wsMeta As Worksheet, wsJson As Worksheet) As String

    Dim lastRawRow As Long, lastMetaRow As Long, lastJsonRow As Long
    lastRawRow = wsRaw.Cells(wsRaw.Rows.Count, "A").End(xlUp).Row
    lastMetaRow = wsMeta.Cells(wsMeta.Rows.Count, "A").End(xlUp).Row
    lastJsonRow = wsJson.Cells(wsJson.Rows.Count, "A").End(xlUp).Row

    Dim convention As String, addendum As String, annotator As String
    Dim domain As String, primaryLang As String, secondaryLang As String
    Dim i As Long
    For i = 2 To lastRawRow
        If Trim(CStr(wsRaw.Cells(i, COL_CONVID).Value)) = convID Then
            convention = wsRaw.Cells(i, COL_CONVENTION).Value
            addendum = wsRaw.Cells(i, COL_ADDENDUM).Value
            annotator = wsRaw.Cells(i, COL_ANNOTATOR).Value
            domain = NormalizeDomain(wsRaw.Cells(i, COL_DOMAIN).Value)
            primaryLang = NormalizeLangCode(wsRaw.Cells(i, COL_PRIMARYLANG).Value)
            secondaryLang = NormalizeSecondaryEnglish(wsRaw.Cells(i, COL_SECONDARYLANG).Value)  ' v9: en / en_IN rule
            Exit For
        End If
    Next i

    ' --- speakers array: No-Speaker(s) first, then the rest (client order) ---
    Dim speakersJSON As String
    Dim spkCount As Long: spkCount = 0
    Dim spkPass As Integer, emitRow As Boolean
    Dim spkRoleLocal As String
    Dim genderOut As String, ageOut As String, nativityOut As String, langsOut As String
    Dim blk As String
    For spkPass = 1 To 2
        For i = 2 To lastMetaRow
            If Trim(CStr(wsMeta.Cells(i, 3).Value)) = convID Then
                spkRoleLocal = Trim(CStr(wsMeta.Cells(i, 6).Value))
                ' v9: pass 1 emits No-Speaker rows, pass 2 emits everyone else.
                emitRow = (spkPass = 1 And spkRoleLocal = "No-Speaker") Or _
                          (spkPass = 2 And spkRoleLocal <> "No-Speaker")
                If emitRow Then
                    If spkCount > 0 Then speakersJSON = speakersJSON & "," & vbCrLf
                    spkCount = spkCount + 1

                    ' Languages and the No-Speaker "NA" attributes depend on role.
                    If spkRoleLocal = "No-Speaker" Then
                        genderOut = "NA"
                        ageOut = "NA"
                        nativityOut = "NA"
                        langsOut = "[]"
                    Else
                        genderOut = CStr(wsMeta.Cells(i, 8).Value)
                        ageOut = CStr(wsMeta.Cells(i, 10).Value)
                        nativityOut = CStr(wsMeta.Cells(i, 11).Value)
                        langsOut = "[""" & JSONEscape(primaryLang) & """, """ & JSONEscape(secondaryLang) & """]"
                    End If

                    ' Key order matches the client V1 layout exactly.
                    blk = ""
                    AddLine blk, "      {"
                    AddLine blk, "        ""speakerId"": """ & JSONEscape(wsMeta.Cells(i, 5).Value) & ""","
                    AddLine blk, "        ""gender"": """ & JSONEscape(genderOut) & ""","
                    AddLine blk, "        ""speaker_age"": """ & JSONEscape(ageOut) & ""","
                    AddLine blk, "        ""genderSource"": """ & JSONEscape(wsMeta.Cells(i, 9).Value) & ""","
                    AddLine blk, "        ""speakerNativity"": """ & JSONEscape(nativityOut) & ""","
                    AddLine blk, "        ""speakerNativitySource"": """ & JSONEscape(wsMeta.Cells(i, 12).Value) & ""","
                    AddLine blk, "        ""speakerRole"": """ & JSONEscape(wsMeta.Cells(i, 6).Value) & ""","
                    AddLine blk, "        ""speakerRoleSource"": """ & JSONEscape(wsMeta.Cells(i, 7).Value) & ""","
                    AddLine blk, "        ""languages"": " & langsOut
                    blk = Left(blk, Len(blk) - Len(vbCrLf))
                    blk = blk & vbCrLf & "      }"

                    speakersJSON = speakersJSON & blk
                End If
            End If
        Next i
    Next spkPass

    ' --- segments array (sorted by Start_Time_Sec) ---
    Dim idxList As Collection
    Set idxList = New Collection
    For i = 2 To lastJsonRow
        If Trim(CStr(wsJson.Cells(i, 1).Value)) = convID Then idxList.Add i
    Next i

    Dim n As Long: n = idxList.Count
    Dim arr() As Long
    If n > 0 Then
        ReDim arr(1 To n)
        For i = 1 To n
            arr(i) = idxList(i)
        Next i
        Dim j As Long, tmp As Long
        For i = 1 To n - 1
            For j = 1 To n - i
                If wsJson.Cells(arr(j), 4).Value > wsJson.Cells(arr(j + 1), 4).Value Then
                    tmp = arr(j): arr(j) = arr(j + 1): arr(j + 1) = tmp
                End If
            Next j
        Next i
    End If

    Dim segmentsJSON As String
    For i = 1 To n
        Dim r As Long: r = arr(i)
        Dim translitVal As String, translitJSON As String
        translitVal = CStr(wsJson.Cells(r, 11).Value)
        If Trim(translitVal) = "" Then
            translitJSON = "null"
        Else
            translitJSON = """" & JSONEscape(translitVal) & """"
        End If

        Dim sblk As String
        sblk = ""
        ' v8: key order matches the client V1 layout exactly.
        AddLine sblk, "      {"
        AddLine sblk, "        ""start"": " & FormatNum(wsJson.Cells(r, 4).Value) & ","
        AddLine sblk, "        ""end"": " & FormatNum(wsJson.Cells(r, 5).Value) & ","
        AddLine sblk, "        ""primaryType"": """ & JSONEscape(wsJson.Cells(r, 6).Value) & ""","
        AddLine sblk, "        ""loudnessLevel"": """ & JSONEscape(wsJson.Cells(r, 7).Value) & ""","
        AddLine sblk, "        ""language"": """ & JSONEscape(wsJson.Cells(r, 8).Value) & ""","
        AddLine sblk, "        ""segmentLanguages"": " & CSVListToJSONArray(wsJson.Cells(r, 9).Value) & ","
        AddLine sblk, "        ""transcriptionData"": {"
        AddLine sblk, "          ""content"": """ & JSONEscape(wsJson.Cells(r, 10).Value) & ""","
        AddLine sblk, "          ""transliteration"": " & translitJSON   ' v8: lowercase per client V1
        AddLine sblk, "        },"
        AddLine sblk, "        ""segmentId"": """ & JSONEscape(wsJson.Cells(r, 2).Value) & ""","
        AddLine sblk, "        ""speakerId"": """ & JSONEscape(wsJson.Cells(r, 3).Value) & """"
        sblk = Left(sblk, Len(sblk) - Len(vbCrLf))
        sblk = sblk & vbCrLf & "      }"

        If i > 1 Then segmentsJSON = segmentsJSON & "," & vbCrLf
        segmentsJSON = segmentsJSON & sblk
    Next i

    Dim varietiesJSON As String
    varietiesJSON = ""
    AddLine varietiesJSON, "      {"
    AddLine varietiesJSON, "        ""languageLocale"": """ & JSONEscape(primaryLang) & ""","
    AddLine varietiesJSON, "        ""languageVariety"": [],"
    AddLine varietiesJSON, "        ""otherLanguageInfluence"": []"
    AddLine varietiesJSON, "      }"
    varietiesJSON = Left(varietiesJSON, Len(varietiesJSON) - Len(vbCrLf))

    Dim out As String
    out = ""
    AddLine out, "{"
    AddLine out, "  ""type"": {"
    AddLine out, "    ""name"": ""MULTI_SPEAKER_LONG_FORM_TRANSCRIPTION"","
    AddLine out, "    ""version"": ""3.2"""
    AddLine out, "  },"
    AddLine out, "  ""value"": {"
    ' v8: value members are ordered exactly as in the client V1 file.
    AddLine out, "    ""languages"": [""" & JSONEscape(primaryLang) & """],"  ' only primary
    AddLine out, "    ""languageInfo"": {"
    AddLine out, "      ""spokenLanguages"": [""" & JSONEscape(primaryLang) & """, """ & JSONEscape(secondaryLang) & """],"
    AddLine out, "      ""speakerDominantVarieties"": ["
    out = out & varietiesJSON & vbCrLf
    AddLine out, "      ]"
    AddLine out, "    },"
    AddLine out, "    ""domainInfo"": {"
    AddLine out, "      ""domainVersion"": ""1.0"","
    AddLine out, "      ""domainList"": [{""domain"": ""Call-center"", ""topicList"": [""" & JSONEscape(domain) & """]}]"  ' array-wrapped per official schema
    AddLine out, "    },"
    AddLine out, "    ""conventionInfo"": {"
    AddLine out, "      ""masterConventionName"": """ & JSONEscape(convention) & ""","
    AddLine out, "      ""customAddendum"": """ & JSONEscape(addendum) & """"
    AddLine out, "    },"
    AddLine out, "    ""annotatorInfo"": {"
    AddLine out, "      ""loginEncrypted"": ""N/A"","
    AddLine out, "      ""annotatorId"": """ & JSONEscape(annotator) & """"
    AddLine out, "    },"
    AddLine out, "    ""speakers"": ["
    out = out & speakersJSON & vbCrLf
    AddLine out, "    ],"
    AddLine out, "    ""segments"": ["
    out = out & segmentsJSON & vbCrLf
    AddLine out, "    ],"
    AddLine out, "    ""taskStatus"": {"
    AddLine out, "      ""segmentation"": {""workflowStatus"": ""COMPLETE"", ""workflowType"": ""LABEL""},"
    AddLine out, "      ""speakerId"": {""workflowStatus"": ""COMPLETE"", ""workflowType"": ""LABEL""},"
    AddLine out, "      ""transcription"": {""workflowStatus"": ""COMPLETE"", ""workflowType"": ""LABEL""}"
    AddLine out, "    }"
    AddLine out, "  }"
    out = out & "}"

    BuildConversationJSON = out
End Function
