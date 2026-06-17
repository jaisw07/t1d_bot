# KrutiDev to Unicode converter
# Adapted from https://gist.github.com/tripleee/b82a79f5b3e57dc6a487ae45077cdbd3

def has_devanagari(text: str) -> bool:
    """Check if text contains any Unicode Devanagari characters."""
    return any('\u0900' <= c <= '\u097F' for c in text)

def is_likely_krutidev(text: str) -> bool:
    """
    Heuristic to guess if ASCII text is actually KrutiDev.
    KrutiDev often contains extended ASCII (>127) or specific punctuation 
    used as letters (/, ;, ], [, {, }, =, +, ~, `, |, \\, ^, _).
    """
    if any(ord(c) > 127 for c in text):
        return True
        
    krutidev_symbols = set("/;][{}~`|^_\\")
    if any(c in krutidev_symbols for c in text):
        return True
        
    common_krutidev = [
        "vk", "bZ", "Fk", "Hk", "Ek", "Yk", "Ok", "Ük", "kS", 
        "nzZ", "xz", "cPp", "ds ", "fy,", ",oa", "ck", "ik", "tk"
    ]
    for pattern in common_krutidev:
        if pattern in text:
            return True
            
    return False

def krutidev_to_unicode(krutidev_substring: str) -> str:
    if not krutidev_substring:
        return ""
        
    modified_substring = krutidev_substring
    
    array_one = ["ñ","Q+Z","sas","aa",")Z","ZZ","‘","’","“","”",
    "å",  "ƒ",  "„",   "…",   "†",   "‡",   "ˆ",   "‰",   "Š",   "‹", 
    "¶+",   "d+", "[+k","[+", "x+",  "T+",  "t+", "M+", "<+", "Q+", ";+", "j+", "u+",
    "Ùk", "Ù", "Dr", "–", "—","é","™","=kk","f=k",  
    "à",   "á",    "â",   "ã",   "ºz",  "º",   "í", "{k", "{", "=",  "«",   
    "Nî",   "Vî",    "Bî",   "Mî",   "<î", "|", "K", "}",
    "J",   "Vª",   "Mª",  "<ªª",  "Nª",   "Ø",  "Ý", "nzZ",  "æ", "ç", "Á", "xz", "#", ":",
    "v‚","vks",  "vkS",  "vk",    "v",  "b±", "Ã",  "bZ",  "b",  "m",  "Å",  ",s",  ",",   "_",
    "ô",  "d", "Dk", "D", "[k", "[", "x","Xk", "X", "Ä", "?k", "?",   "³", 
    "pkS",  "p", "Pk", "P",  "N",  "t", "Tk", "T",  ">", "÷", "¥",
    "k+",  "k",  "V",  "B",   "ì",   "ï", "M+", "<+", "M",  "<", ".k", ".",    
    "r",  "Rk", "R",   "Fk", "F",  ")", "n", "/k", "èk",  "/", "Ë", "è", "u", "Uk", "U",   
    "i",  "Ik", "I",   "Q",    "¶",  "c", "Ck",  "C",  "Hk",  "H", "e", "Ek",  "E",
    ";",  "¸",   "j",    "y", "Yk",  "Y",  "G",  "o", "Ok", "O",
    "'k", "'",   "\"k",  "\"",  "l", "Lk",  "L",   "g", 
    "È", "z", 
    "Ì", "Í", "Î",  "Ï",  "Ñ",  "Ò",  "Ó",  "Ô",   "Ö",  "Ø",  "Ù","Ük", "Ü",
    "‚",    "ks",   "kS",   "k",  "h",    "q",   "w",   "`",    "s",    "S",
    "a",    "¡",    "%",     "W",  "•", "·", "∙", "·", "~j",  "~", "\\","+"," ः",
    "^", "*",  "Þ", "ß", "(", "¼", "½", "¿", "À", "¾", "A", "-", "&", "&", "Œ", "]","~ ","@"]
    
    array_two = ["॰","QZ+","sa","a","र्द्ध","Z","\"","\"","'","'",
    "०",  "१",  "२",  "३",     "४",   "५",  "६",   "७",   "८",   "९",   
    "फ़्",  "क़",  "ख़", "ख़्",  "ग़", "ज़्", "ज़",  "ड़",  "ढ़",   "फ़",  "य़",  "ऱ",  "ऩ",    
    "त्त", "त्त्", "क्त",  "दृ",  "कृ","nn","nna","=k","f=",
    "ह्न",  "ह्य",  "हृ",  "ह्म",  "ह्र",  "ह्",   "द्द",  "क्ष", "क्ष्", "त्र", "त्र्", 
    "छ्य",  "ट्य",  "ठ्य",  "ड्य",  "ढ्य", "द्य", "ज्ञ", "द्व",
    "श्र",  "ट्र",    "ड्र",    "ढ्र",    "छ्र",   "क्र",  "फ्र", "र्द्र",  "द्र",   "प्र", "प्र",  "ग्र", "रु",  "रू",
    "ऑ",   "ओ",  "औ",  "आ",   "अ", "ईं", "ई",  "ई",   "इ",  "उ",   "ऊ",  "ऐ",  "ए", "ऋ",
    "क्क", "क", "क", "क्", "ख", "ख्", "ग", "ग", "ग्", "घ", "घ", "घ्", "ङ",
    "चै",  "च", "च", "च्", "छ", "ज", "ज", "ज्",  "झ",  "झ्", "ञ",
    "ा",  "ा",   "ट",   "ठ",   "ड्ड",   "ड्ढ",  "ड़", "ढ़", "ड",   "ढ", "ण", "ण्",   
    "त", "त", "त्", "थ", "थ्",  "द्ध",  "द", "ध", "ध", "ध्", "ध्", "ध्", "न", "न", "न्",    
    "प", "प", "प्",  "फ", "फ्",  "ब", "ब", "ब्",  "भ", "भ्",  "म",  "म", "म्",  
    "य", "य्",  "र", "ल", "ल", "ल्",  "ळ",  "व", "व", "व्",   
    "श", "श्",  "ष", "ष्", "स", "स", "स्", "ह", 
    "ीं", "्र",    
    "द्द", "ट्ट","ट्ठ","ड्ड","कृ","भ","्य","ड्ढ","झ्","क्र","त्त्","श","श्",
    "ॉ",  "ो",   "ौ",   "ा",   "ी",   "ु",   "ू",   "ृ",   "े",   "ै",
    "ं",   "ँ",   "ः",   "ॅ",  "ऽ", "ऽ", "ऽ", "ऽ", "्र",  "्", "?", "़",":",
    "‘",   "’",   "“",   "”",  ";",  "(",    ")",   "{",    "}",   "=", "।", ".", "-",  "µ", "॰", ",","् ","/"]
    
    # Specialty characters
    
    # Move "f" to correct position and replace
    modified_substring = "  " + modified_substring + "  "
    position_of_f = modified_substring.rfind("f")
    while position_of_f != -1:    
        modified_substring = modified_substring[:position_of_f] + modified_substring[position_of_f+1] + modified_substring[position_of_f] + modified_substring[position_of_f+2:]
        position_of_f = modified_substring.rfind("f", 0, position_of_f - 1)
    modified_substring = modified_substring.replace("f", "ि")
    modified_substring = modified_substring.strip()
    
    # Move "half R" to correct position and replace
    modified_substring = "  " + modified_substring + "  "
    position_of_r = modified_substring.find("Z")
    set_of_matras = ["‚", "ks", "kS", "k", "h", "q", "w", "`", "s", "S", "a", "¡", "%", "W", "·", "~ ", "~"]
    while position_of_r != -1:    
        modified_substring = modified_substring.replace("Z", "", 1)
        if modified_substring[position_of_r - 1] in set_of_matras:
            modified_substring = modified_substring[:position_of_r - 2] + "j~" + modified_substring[position_of_r - 2:]
        else:
            modified_substring = modified_substring[:position_of_r - 1] + "j~" + modified_substring[position_of_r - 1:]
        position_of_r = modified_substring.find("Z")
    modified_substring = modified_substring.strip()
    
    # Replace ASCII with Unicode
    for input_symbol_idx in range(len(array_one)):
        modified_substring = modified_substring.replace(array_one[input_symbol_idx], array_two[input_symbol_idx])
    
    return modified_substring
