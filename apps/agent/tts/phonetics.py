import re

# Dictionary mapping Romanized Hindi/Hinglish terms to phonetic spelling optimized for Kokoro-82M (en-us phonemizer)
HINGLISH_PHONETIC_MAP = {
    r"\bnamaste\b": "Nuh-muh-stay",
    r"\bnamaskar\b": "Nuh-muhs-kaar",
    r"\bswagat\b": "swaa-gut",
    r"\bshukriya\b": "shook-ree-yaa",
    r"\bdhanyavad\b": "dhun-yuh-vaad",
    r"\bkaise\b": "kay-say",
    r"\bkaisi\b": "kay-see",
    r"\bkaisa\b": "kay-saa",
    r"\bkya\b": "kyaa",
    r"\bkyun\b": "kyoon",
    r"\bkyu\b": "kyoo",
    r"\bnahi\b": "nah-hee",
    r"\bnahin\b": "nah-heen",
    r"\bhaan\b": "haahn",
    r"\bhoon\b": "hoon",
    r"\bhai\b": "hai",
    r"\bhain\b": "hain",
    r"\bho\b": "ho",
    r"\bboliye\b": "boh-lee-yay",
    r"\bbaat\b": "baath",
    r"\bbataye\b": "buh-taayay",
    r"\bbataiye\b": "buh-taa-ee-yay",
    r"\bbataiyega\b": "buh-taa-ee-yay-gah",
    r"\bbataunga\b": "buh-taa-oong-gah",
    r"\bbataungi\b": "buh-taa-oong-gee",
    r"\bsuno\b": "soo-no",
    r"\bsun\b": "soon",
    r"\braha\b": "ruh-haa",
    r"\brahi\b": "ruh-hee",
    r"\brahe\b": "ruh-hay",
    r"\baap\b": "ahp",
    r"\baapka\b": "ahp-kaa",
    r"\baapke\b": "ahp-kay",
    r"\baapki\b": "ahp-kee",
    r"\btum\b": "toom",
    r"\btumhara\b": "toom-haa-raa",
    r"\bmera\b": "may-raa",
    r"\bmeri\b": "may-ree",
    r"\bmere\b": "may-ray",
    r"\bmain\b": "mai",
    r"\bhum\b": "hoom",
    r"\bunhe\b": "oon-hay",
    r"\bunka\b": "oon-kaa",
    r"\bunke\b": "oon-kay",
    r"\bunki\b": "oon-kee",
    r"\bkal\b": "kuhl",
    r"\baaj\b": "aaj",
    r"\bparson\b": "puhr-soh",
    r"\bturantam\b": "too-runt",
    r"\bturant\b": "too-runt",
    r"\bjaldi\b": "jul-dee",
    r"\bthik\b": "theek",
    r"\btheek\b": "theek",
    r"\baccha\b": "uch-haa",
    r"\bacha\b": "uch-haa",
    r"\bachha\b": "uch-haa",
    r"\bbilkul\b": "bil-kool",
    r"\bzaroor\b": "zuh-roor",
    r"\bchahiye\b": "chaa-hee-yay",
    r"\bkarwa\b": "kuhr-waa",
    r"\bkarwao\b": "kuhr-waao",
    r"\bdenge\b": "dayn-gay",
    r"\bdunga\b": "doon-gah",
    r"\bdungi\b": "doon-gee",
    r"\bkijiye\b": "kee-jee-yay",
    r"\bkarunga\b": "kuh-roon-gah",
    r"\bkarungi\b": "kuh-roon-gee",
    r"\bManan\b": "Muh-nun",
}


def preprocess_hinglish_for_tts(text: str) -> str:
    """Transform Hinglish/Hindi Romanized terms into phonetically natural pronunciations for Kokoro TTS."""
    if not text:
        return text

    processed = text
    for pattern, replacement in HINGLISH_PHONETIC_MAP.items():
        processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

    # Clean up double hyphens or spacing irregularities
    processed = re.sub(r"\s+", " ", processed).strip()
    return processed
