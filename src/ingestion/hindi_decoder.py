import re

def is_scrambled_hindi(text: str) -> bool:
    """
    Check if the text contains signature scrambled words from the Hindi booklet.
    This ensures we only decode text that actually needs it.
    """
    if not text:
        return False
    signatures = ["भधुभेह", "इआसुलरन", "इन् सूलरन", "फीभाियमों", "ऩहरे", "यात के"]
    return any(sig in text for sig in signatures)

def decode_hindi_text(text: str) -> str:
    """
    Decodes scrambled Hindi text extracted from PDFs with custom/buggy font encodings
    back into standard Unicode Devanagari.
    """
    if not text:
        return ""
        
    # 1. Apply word-level replacements first to protect specific terms
    replacements = {
        "एं जक्टआग": "इंजेक्शन",
        "इआसुलरन": "इंसुलिन",
        "इंसूलरिन": "इंसुलिन",
        "इन्सूलरिन": "इंसुलिन",
        "खुयाक": "खुराक",
        "फढ़ाएं": "बढ़ाएं",
        "यात": "रात",
        "ऩहरे": "पहले",
        "य वऩ्": "या फिर",
        "वऩ्": "फिर",
        "भधुभेह": "मधुमेह",
        "गरूक ज़": "ग्लूकोज",
        "ग् रूक ज़": "ग्लूकोज",
        "करियमाज": "क्रियाज",
        "करियमाज़": "क्रियाज",
        "ऩ करियमाज": "पैंक्रियाज",
        "ऩ करियमाज़": "पैंक्रियाज",
        "ग्राआथी": "ग्रंथि",
        "हाभ न": "हार्मोन",
        "ऩ  दा": "पैदा",
        "ऩ दा": "पैदा",
        "ह  ता": "होता",
        "ह ता": "होता",
        "हभाये": "हमारे",
        "लबन् न": "भिन्न",
        "अआगों": "अंगों",
        "उऩम चगता": "उपयोगिता",
        "फढाकय": "बढ़ाकर",
        "शूगय": "शुगर",
        "िनमआ्रितत": "नियंत्रित",
        "टाईऩ": "टाईप",
        "टाऩ": "टाईप",
        "्फस् तय": "बिस्तर",
        "फच् चों": "बच्चों",
        "प् मास": "प्यास",
        "व् मवाहाय": "व्यवहार",
        "अभाश् म": "आमाशय",
        "ह  जाता": "हो जाता",
        "ह  सकती": "हो सकती",
        "ह  सकता": "हो सकता",
        "ह  ती": "होती",
        "फआद": "बंद",
        "इसलरएं": "इसलिए",
        "इसलरए": "इसलिए",
        "रऺण": "लक्षण",
        "क क": "कई",
        "र गों": "लोगों",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 2. Pre-process specific character combinations
    # 'गो' after a consonant (with or without 'ा') represents a reph (U+0930 + U+094d) on that consonant.
    # Pattern: (Consonant)(ा)?गो -> र्(Consonant)(ा)
    consonant_pat = r"([\u0915-\u0939\u0958-\u095f\u0929])(ा)?गो"
    text = re.sub(consonant_pat, r"र्\1\2", text)
    
    # 3. Map individual character replacements
    char_map = {
        'भ': 'म',
        'फ': 'ब',
        'ब': 'भ',
        'य': 'र',
        'र': 'ल',
        'ज': 'ज',
        'ऩ': 'प',
        'व': 'फ',
        'ऺ': 'क्ष',
        'ू': 'ु',
    }
    
    # We will do a character-by-character pass to handle positional rules
    chars = list(text)
    n = len(chars)
    i = 0
    decoded_chars = []
    
    devanagari_consonants = set(
        chr(c) for c in range(0x0915, 0x093a)
    ) | {'ऩ', 'फ़', 'क़', 'ग़', 'ज़', 'ड़', 'ढ़', 'फ़', 'ब', 'फ', 'भ', 'य'}
    
    while i < n:
        c = chars[i]
        
        # Rule for 'र्' (reph / half-r) - should remain 'र्' and not be mapped to 'ल्'
        if c == 'र' and i + 1 < n and chars[i+1] == '्':
            decoded_chars.append('र')
            decoded_chars.append('्')
            i += 2
            continue
            
        # Rule for 'ि' (short i matra) represented by 'च', 'ल', 'र', 'ज', 'ऩ' before a consonant
        # If one of these is followed by a consonant, it becomes 'ि' and is placed AFTER the consonant in Unicode.
        if c in {'च', 'ल', 'र', 'ज', 'ऩ'} and i + 1 < n and chars[i+1] in devanagari_consonants:
            next_c = chars[i+1]
            mapped_next_c = char_map.get(next_c, next_c)
            decoded_chars.append(mapped_next_c)
            decoded_chars.append('ि')
            i += 2
            continue
            
        # Rule for 'आ' mapping to 'ं' (anusvara) when it follows a consonant or a matra
        if c == 'आ' and i - 1 >= 0 and (chars[i-1] in devanagari_consonants or chars[i-1] in {'ा', 'ु', 'ू', 'ो', 'े', 'ै', 'ि', 'ी'}):
            decoded_chars.append('ं')
            i += 1
            continue

        # Rule for 'य' mapping to 'या' when it's a standalone word or followed by space (representing 'या')
        if c == 'य' and (i + 1 == n or chars[i+1].isspace()) and (i - 1 >= 0 and chars[i-1].isspace()):
            decoded_chars.append('या')
            i += 1
            continue
            
        # Default mapping
        decoded_chars.append(char_map.get(c, c))
        i += 1
        
    return "".join(decoded_chars)
