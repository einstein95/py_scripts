def EncryptString(argMsg, argKey):
    sOut = ""
    iKeyLength = len(argKey)
    iMsgLength = len(argMsg)
    iKeyIndex = 1
    iMsgIndex = 1
    for i in range(16):
        iMsgChar = ord(argMsg[iMsgIndex - 1])
        iKeyChar = ord(argKey[iKeyIndex - 1])
        myBit = iMsgChar ^ iKeyChar
        if myBit >= 97 and myBit <= 122:  # if myBit in [a-z], convert to [A-Z]
            myBit -= 32
        else:
            myBit = 65 + iKeyIndex + iMsgIndex
            if myBit > 90:
                myBit = 90

        sOutChar = chr(myBit)
        sOut += sOutChar
        iKeyIndex += 1
        iMsgIndex += 1
        if iKeyIndex > iKeyLength:
            iKeyIndex = 1

        if iMsgIndex > iMsgLength:
            iMsgIndex = 1

    return sOut


def CheckKey(wName, wKey, wInts):
    for n in wInts:
        print(wName, wKey, n)
        if makeKeyName(wName, n) == wKey:
            print(wName, wKey, n)


def makeKeyName(wName, wCode):
    wName = "".join([i for i in wName if not i.isspace()])
    if len(wName) == 0:
        return "NOMATCH"
    wName = wName.upper()
    while len(wName) < 16:
        wName += wName

    mKey2 = EncryptString(wName, wCode)
    return mKey2


print(makeKeyName("Macintosh_Garden", "9183624617257869"))
# TPGZXFOEYHUTEZSW