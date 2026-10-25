"""Turn script text into English visual keywords so images match the topic.

Bangla has no reliable offline translator in the free stack, so common words are
mapped through a curated dictionary. If an AI provider is configured the app can ask
it for better per-scene prompts instead (see core.script_ai).
"""
import re

BANGLA_TERMS = {
    # ---------------------------------------------------------------- nature
    "নদী": "river", "নৌকা": "wooden boat on water", "সাগর": "sea", "সমুদ্র": "sea",
    "পাহাড়": "mountain", "পর্বত": "mountain", "পাহাড়ি": "mountain landscape",
    "জঙ্গল": "forest", "বন": "forest", "গাছ": "tree", "গাছপালা": "green trees",
    "ফুল": "flowers", "পাখি": "bird", "আকাশ": "blue sky", "মেঘ": "clouds",
    "বৃষ্টি": "rain", "রোদ": "sunlight", "সূর্য": "sun", "চাঁদ": "moon",
    "তারা": "starry night sky", "সবুজ": "green nature", "ধান": "paddy field",
    "ধানখেত": "rice field", "খেত": "farm field", "মাঠ": "open field",
    "গ্রাম": "rural village", "বাংলাদেশ": "bangladesh countryside",
    "বাংলা": "bangladesh culture", "ঢাকা": "dhaka city", "শহর": "city skyline",
    "রাস্তা": "road", "সমুদ্রসৈকত": "beach", "ঝর্ণা": "waterfall", "হ্রদ": "lake",
    "মাটি": "soil", "পানি": "glass of water", "আলো": "warm light", "ছায়া": "soft shadows",
    "দ্বীপ": "island", "চর": "river sandbank", "বিল": "wetland", "হাওর": "wetland",
    # ------------------------------------------------------------- agriculture
    "কৃষক": "farmer working", "কৃষি": "agriculture farming", "ফসল": "crop harvest",
    "ফলন": "harvested grain", "মৌসুম": "seasonal farm work", "জমি": "farmland",
    "বীজ": "seeds in hand", "সার": "fertilizer", "সেচ": "irrigation water",
    "গরু": "cow in a field", "ছাগল": "goat", "হাঁস": "duck", "মুরগি": "chicken",
    "মাছ": "fish", "মাছধরা": "fishing net", "কাটা": "harvesting", "ধানকাটা": "rice harvest",
    # -------------------------------------------------------------------- food
    "ভাত": "cooked rice", "সবজি": "fresh vegetables", "ফল": "fresh fruits",
    "দুধ": "glass of milk", "চা": "cup of tea", "রুটি": "bread", "মিষ্টি": "sweets",
    "রান্না": "cooking in a kitchen", "খাবার": "food on a table", "খাদ্য": "fresh food",
    "রেসিপি": "recipe ingredients", "মসলা": "spices", "মাংস": "meat dish",
    # ---------------------------------------------------------------- education
    "শিক্ষা": "classroom learning", "স্কুল": "school building", "কলেজ": "college campus",
    "বিশ্ববিদ্যালয়": "university campus", "বই": "open book", "পরীক্ষা": "exam paper",
    "ছাত্র": "student studying", "শিক্ষক": "teacher", "জ্ঞান": "books and knowledge",
    "শেখা": "learning and growth", "পড়া": "reading a book", "লেখা": "writing in a notebook",
    "ক্লাস": "classroom", "হোমওয়ার্ক": "notebook and pencil",
    # ------------------------------------------------------------- religion
    "ইসলাম": "mosque architecture", "মুসলিম": "mosque", "নামাজ": "prayer mat",
    "কুরআন": "open holy book", "হাদিস": "islamic calligraphy", "আল্লাহ": "mosque dome",
    "মসজিদ": "mosque architecture", "রোজা": "iftar table", "ঈদ": "festive celebration",
    "দুআ": "praying hands", "ধর্ম": "place of worship", "মন্দির": "temple architecture",
    "পূজা": "temple lamps", "বৌদ্ধ": "buddhist temple", "উৎসব": "colorful festival",
    "নবী": "historic mosque", "জুম্মা": "crowded mosque",
    # ------------------------------------------------------------- society
    "রাজনীতি": "government building", "সরকার": "government building",
    "নির্বাচন": "voting ballot box", "আইন": "law books", "দেশ": "national flag",
    "জাতি": "people of a nation", "স্বাধীনতা": "flag waving", "যুদ্ধ": "historic battlefield",
    "শান্তি": "peaceful landscape", "সমাজ": "community gathering", "মানুষ": "people",
    "জনসাধারণ": "crowd of people", "নেতা": "leader speaking", "সভা": "meeting room",
    # ---------------------------------------------------------------- business
    "ব্যবসা": "business meeting", "অর্থ": "money and finance", "টাকা": "money",
    "বিনিয়োগ": "investment charts", "লাভ": "growth chart", "বাজার": "bustling market",
    "দোকান": "small shop", "ব্যাংক": "bank building", "চাকরি": "office workplace",
    "কোম্পানি": "modern office", "উদ্যোক্তা": "startup founder working",
    "বিক্রয়": "shopping and sales", "ক্রেতা": "customer shopping",
    # ------------------------------------------------------------------- tech
    "প্রযুক্তি": "modern technology", "কম্পিউটার": "computer setup",
    "মোবাইল": "smartphone in hand", "ফোন": "smartphone", "ইন্টারনেট": "network cables",
    "রোবট": "humanoid robot", "কৃত্রিম": "artificial intelligence concept",
    "বুদ্ধিমত্তা": "artificial intelligence neural network", "ডেটা": "data visualization",
    "কোড": "programming code on screen", "সফটওয়্যার": "software interface",
    "অ্যাপ": "mobile app interface", "নিরাপত্তা": "cybersecurity concept",
    "মেশিন": "industrial machine", "যন্ত্র": "machine gears", "ক্যামেরা": "camera",
    "ছবি": "photography", "ভিডিও": "video camera", "গেম": "video game screen",
    "ইন্টারনেটের": "network cables", "সোশ্যাল": "social media on phone",
    # ----------------------------------------------------------------- health
    "স্বাস্থ্য": "healthy lifestyle", "শরীর": "human body fitness",
    "ব্যায়াম": "exercise workout", "ঘুম": "peaceful sleep", "বিশ্রাম": "rest and calm",
    "মন": "mindfulness meditation", "মেডিটেশন": "meditation", "যোগব্যায়াম": "yoga pose",
    "হাসপাতাল": "hospital corridor", "ওষুধ": "medicine", "ঔষধ": "medicine",
    "ডাক্তার": "doctor in a clinic", "রোগ": "medical checkup", "সুস্থ": "healthy person",
    "খেলাধুলা": "sports activity",
    # ---------------------------------------------------------------- sports
    "খেলা": "sports action", "ফুটবল": "football match", "ক্রিকেট": "cricket match",
    "খেলোয়াড়": "sports player", "জয়": "victory celebration", "পরাজয়": "defeat moment",
    "স্টেডিয়াম": "stadium crowd", "দৌড়": "person running",
    # ---------------------------------------------------------------- travel
    "ভ্রমণ": "travel landscape", "পর্যটন": "tourist landmark", "ট্রেন": "train journey",
    "বাস": "bus on a road", "বিমান": "airplane in the sky", "হাঁটা": "person walking",
    "রিকশা": "rickshaw on a street", "সেতু": "bridge over water", "বন্দর": "harbour",
    # -------------------------------------------------------------- emotions
    "ভালোবাসা": "warm loving moment", "দুঃখ": "sad reflective person",
    "আনন্দ": "joyful celebration", "রাগ": "tense dramatic moment",
    "ভয়": "dramatic dark scene", "আশা": "hopeful sunrise",
    "স্বপ্ন": "person looking at horizon", "সাহস": "courageous silhouette",
    "শ্রদ্ধা": "respectful gesture", "একতা": "people together",
    # ---------------------------------------------------------------- family
    "মা": "mother and child", "বাবা": "father and child", "পরিবার": "family together",
    "সন্তান": "child playing", "শিশু": "child playing", "বন্ধু": "friends together",
    "ভাই": "brothers", "বোন": "sisters", "দাদা": "grandfather",
    "দাদি": "grandmother", "বিয়ে": "wedding ceremony", "ঘর": "cozy home interior",
    # ---------------------------------------------------------------- people
    "ছেলে": "young man", "মেয়ে": "young woman", "নারী": "woman",
    "বৃদ্ধ": "elderly person", "কর্মী": "worker", "শ্রমিক": "labourer working",
    "গায়ক": "singer on stage", "শিল্পী": "artist painting", "খেটে": "hard working person",
    # ------------------------------------------------------------- motivation
    "সাফল্য": "person reaching the summit", "সফল": "achievement celebration",
    "লক্ষ্য": "target and focus", "পরিশ্রম": "hard working person",
    "ধৈর্য": "patient persistence", "শৃঙ্খলা": "disciplined routine",
    "অভ্যাস": "daily habit routine", "সময়": "clock and time", "পথ": "long open road",
    "যাত্রা": "journey on a road", "শক্তি": "strong determined person",
    "পরিবর্তন": "transformation scene", "ব্যর্থতা": "person standing up again",
    "অনুপ্রেরণা": "inspiring sunrise silhouette", "সাহায্য": "helping hands",
    # ------------------------------------------------------------------ time
    "সকাল": "morning light", "দুপুর": "midday sun", "সন্ধ্যা": "evening sky",
    "রাত": "night scene", "দিন": "daylight scene", "বছর": "calendar",
    "মাস": "calendar", "ঘণ্টা": "clock face",
    # ------------------------------------------------------------------- art
    "গান": "music performance", "নাচ": "dance movement", "সিনেমা": "cinema screen",
    "নাটক": "theatre stage", "ছবিআঁকা": "painting", "রং": "colorful paint",
    "কবিতা": "poetry book", "গল্প": "open storybook", "ইতিহাস": "ancient historic architecture",
    "সংস্কৃতি": "cultural heritage", "ঐতিহ্য": "traditional heritage craft",
    # ------------------------------------------------------------- conflicts
    "দুর্নীতি": "serious news scene", "অপরাধ": "police lights at night",
    "বিপদ": "warning scene", "দুর্যোগ": "storm clouds", "বন্যা": "flooded street",
    "খরা": "dry cracked earth",
    # ---------------------------------------------------------- professions
    "ইঞ্জিনিয়ার": "engineer at work", "পুলিশ": "police officer",
    "সৈনিক": "soldier", "জেলে": "fisherman with net", "কামার": "blacksmith at work",
    "তাঁতি": "handloom weaving", "দর্জি": "tailor sewing", "বাবুর্চি": "chef cooking",
    "ড্রাইভার": "bus driver", "পাইলট": "airplane cockpit", "আইনজীবী": "lawyer in court",
    "সাংবাদিক": "reporter with microphone", "ব্যবসায়ী": "shopkeeper",
    # -------------------------------------------------------------- objects
    "চেয়ার": "wooden chair", "টেবিল": "table", "দরজা": "door", "জানালা": "window light",
    "আয়না": "mirror reflection", "ঘড়ি": "clock face", "চশমা": "eyeglasses",
    "জুতা": "shoes", "কাপড়": "folded clothes", "থালা": "plate of food",
    "বালিশ": "pillow", "বিছানা": "bed", "চুলা": "cooking stove",
    "হাতুড়ি": "hammer and tools", "কাগজ": "paper sheets", "কলম": "pen writing",
    "পেন্সিল": "pencil sketch", "ব্যাগ": "school bag",
    # -------------------------------------------------------------- vehicles
    "গাড়ি": "car on a road", "মোটরসাইকেল": "motorcycle", "সাইকেল": "bicycle",
    "জাহাজ": "cargo ship", "লঞ্চ": "river ferry", "ঘোড়া": "horse running",
    "উট": "camel in desert", "হাতি": "elephant",
    # --------------------------------------------------------------- weather
    "গরম": "hot sunny day", "ঠান্ডা": "cold winter scene", "শীত": "winter morning",
    "বর্ষা": "monsoon rain", "ঝড়": "storm wind", "কুয়াশা": "foggy morning",
    "বজ্র": "lightning storm", "তুষার": "snowfall",
    # ------------------------------------------------------------ adjectives
    "সুন্দর": "beautiful scenery", "বড়": "wide establishing shot",
    "ছোট": "small intimate detail", "নতুন": "fresh modern scene", "পুরানো": "vintage old scene",
    "দ্রুত": "fast motion blur", "ধীর": "slow calm scene", "কঠিন": "challenging steep climb",
    "সহজ": "simple clean scene", "সেরা": "peak achievement moment", "খারাপ": "gloomy scene",
    # ----------------------------------------------------------- action verbs
    "খাওয়া": "person eating", "ঘুমানো": "person sleeping", "দৌড়ানো": "person running",
    "লাফানো": "person jumping", "হাসা": "laughing person", "কাঁদা": "crying person",
    "দেখা": "person looking at a view", "শোনা": "person listening with headphones",
    "বলা": "person speaking", "ধরা": "hands holding", "ছোঁয়া": "hand touching",
    "কেনা": "shopping and buying", "বিক্রি": "selling at a stall",
    # ------------------------------------------------------------- abstract
    "সত্য": "honest open sky", "মিথ্যা": "shadowed deceptive scene",
    "ন্যায়": "scales of justice", "যত্ন": "caring hands", "সম্মান": "respectful bow",
    "দায়িত্ব": "responsible person working", "বিশ্বাস": "trusting handshake",
    "প্রতিশ্রুতি": "promise with clasped hands", "ভবিষ্যৎ": "futuristic bright horizon",
    "অতীত": "faded historical photo", "বর্তমান": "present day street",
    # ---------------------------------------------------- nature and matter
    "পাথর": "rocks", "বালি": "sand", "ধুলো": "dusty road", "আগুন": "open fire",
    "ধোঁয়া": "smoke", "বাতাস": "wind in trees", "ঢেউ": "waves", "জোয়ার": "high tide",
    "ভাটা": "low tide", "মরুভূমি": "desert dunes",
    # -------------------------------------------------------------- animals
    "কুকুর": "dog", "বিড়াল": "cat", "বাঘ": "tiger", "সিংহ": "lion", "বানর": "monkey",
    "সাপ": "snake", "মশা": "mosquito", "পোকা": "insect closeup", "মৌমাছি": "bee on flower",
    # ----------------------------------------------------------------- food
    "ডিম": "eggs", "চিনি": "sugar", "লবণ": "salt", "তেল": "cooking oil", "ঘি": "ghee",
    "মাখন": "butter", "কলা": "bananas", "আম": "mangoes", "কাঁঠাল": "jackfruit",
    "লিচু": "lychees", "নারকেল": "coconut", "পেঁপে": "papaya",
    # --------------------------------------------------------------- places
    "মেলা": "village fair", "পার্ক": "green park", "জাদুঘর": "museum interior",
    "স্টেশন": "railway station", "বিমানবন্দর": "airport terminal", "থানা": "police station",
    "আদালত": "courtroom", "বাড়ি": "house exterior", "অট্টালিকা": "high rise building",
    # --------------------------------------------------------------- online
    "ওয়েবসাইট": "web page on screen", "ইউটিউব": "video platform on screen",
    "ফেসবুক": "social feed on phone", "অনলাইন": "online work on laptop",
    "ডিজিটাল": "digital devices", "স্মার্টফোন": "smartphone",
    "ব্যাটারি": "battery", "চার্জার": "phone charger",
    # ---------------------------------------------------------------- time
    "সপ্তাহ": "weekly calendar", "মিনিট": "clock hands", "সেকেন্ড": "clock ticking",
    "আজ": "present day scene", "গতকাল": "yesterday memory", "ভোর": "dawn light",
    "মধ্যরাত": "midnight sky", "ঋতু": "seasonal landscape",
    # ------------------------------------------------------------- feelings
    "খুশি": "happy person", "দুশ্চিন্তা": "worried person", "একাকীত্ব": "lonely figure",
    "ভরসা": "supportive hand", "গর্ব": "proud moment", "লজ্জা": "shy person",
    # ---------------------------------------------------------------- money
    "দাম": "price tags", "ক্ষতি": "loss and setback", "ঋণ": "loan documents",
    "বেতন": "salary payment", "সঞ্চয়": "savings jar", "দারিদ্র্য": "humble village home",
    # ------------------------------------------------------------ religion
    "ইমান": "peaceful mosque interior", "তাওবা": "praying hands",
    "জান্নাত": "beautiful garden", "হজ": "pilgrims at kaaba",
    "জাকাত": "charity giving",
    # ------------------------------------------------------------- music art
    "গিটার": "guitar", "তবলা": "tabla drums", "বাঁশি": "flute", "সুর": "musical notes",
    "তাল": "rhythm percussion",
}

ENGLISH_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you", "are", "was",
    "were", "have", "has", "had", "not", "but", "can", "will", "would", "could",
    "should", "about", "into", "over", "more", "most", "some", "any", "all", "every",
    "much", "many", "very", "just", "only", "also", "than", "then", "them", "they",
    "their", "there", "here", "when", "what", "which", "who", "why", "how", "its",
    "it's", "of", "to", "in", "on", "at", "by", "as", "is", "be", "been", "being",
    "do", "does", "did", "so", "if", "or", "no", "yes", "out", "up", "down", "we",
    "our", "us", "i", "my", "me", "he", "she", "his", "her", "him", "one", "two",
    "three", "five", "seven", "ten", "get", "got", "make", "made", "take", "took",
    "like", "want", "need", "know", "think", "see", "look", "come", "go", "going",
    "today", "tomorrow", "yesterday", "now", "new", "good", "best", "great", "more",
    # words that carry no visual meaning in a video prompt
    "fact", "facts", "never", "knew", "know", "known", "video", "videos", "thing",
    "things", "way", "ways", "secret", "secrets", "amazing", "shocking", "crazy",
    "unbelievable", "watch", "subscribe", "share", "comment", "channel", "shorts",
    "reels", "tips", "guide", "explained", "revealed", "top", "did", "does", "here",
    "there", "something", "anything", "everything", "nothing", "everyone", "someone",
    "anyone", "must", "need", "needs", "really", "actually", "because", "before",
    "after", "while", "during", "these", "those", "been", "being", "having", "let",
    "lets", "get", "gets", "getting", "keep", "keeps", "start", "starts", "today's",
}

# Bangla suffixes, longest first — নদীটি / নদীর / নদীতে all map back to নদী
BANGLA_SUFFIXES = [
    "গুলোর", "গুলির", "গুলোকে", "গুলিকে", "গুলো", "গুলি", "দেরকে", "দের",
    "টার", "টির", "টাকে", "টিকে", "টাতে", "টিতে", "টা", "টি",
    "খানা", "খানি", "য়ের", "য়েরই", "ের", "য়ে", "তে", "কে", "রা", "র", "ে",
]

STYLE_FALLBACK = {
    "cinematic": "cinematic establishing shot, dramatic light",
    "dramatic": "dramatic moody scene with strong contrast",
    "educational": "clean modern illustration",
    "tutorial": "clean bright instructional scene",
    "vibrant": "colorful energetic scene",
    "anime": "anime style scenery",
    "cartoon2d": "flat 2d illustration",
    "whiteboard": "whiteboard drawing",
    "sketch": "pencil sketch",
    "realistic": "photorealistic natural scene",
    "slide": "minimal clean background",
    "puppet": "cute puppet character scene",
}


def is_bangla(text):
    return bool(re.search(r"[\u0980-\u09FF]", text or ""))


def _stem_candidates(word):
    """The word plus every sensible suffix-stripped form."""
    candidates = [word]
    for suffix in BANGLA_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[:-len(suffix)]
            if stem not in candidates:
                candidates.append(stem)
    return candidates


def _lookup(word):
    for candidate in _stem_candidates(word):
        if candidate in BANGLA_TERMS:
            return BANGLA_TERMS[candidate]
    return None


def extract_keywords(text, limit=5):
    """Pull visual keywords out of a sentence (Bangla mapped, English filtered)."""
    text = (text or "").strip()
    if not text:
        return []
    found = []
    if is_bangla(text):
        for raw in re.findall(r"[\u0980-\u09FF]+", text):
            value = _lookup(raw.rstrip("।,,"))
            if value and value not in found:
                found.append(value)
            if len(found) >= limit:
                break
    for word in re.findall(r"[A-Za-z][A-Za-z\-']+", text):
        lowered = word.lower()
        if lowered in ENGLISH_STOPWORDS or len(lowered) < 3 or lowered in found:
            continue
        found.append(lowered)
        if len(found) >= limit:
            break
    return found[:limit]


def matched_keywords(scene_text, topic="", style="cinematic", limit=5):
    """Return (keywords, matched). matched=False means a generic fallback was used."""
    keywords = extract_keywords(scene_text, limit=limit)
    if topic:
        for word in extract_keywords(topic, limit=2):
            if word not in keywords:
                keywords.insert(0, word)
    matched = bool(keywords)
    if not keywords:
        keywords = [STYLE_FALLBACK.get(style, "cinematic scene")]
    return keywords[:max(1, limit)], matched


def visual_keywords(scene_text, topic="", style="cinematic", limit=5):
    """Best-effort English visual phrase for one scene."""
    return matched_keywords(scene_text, topic, style, limit)[0]


def search_query(scene_text, topic="", max_words=4):
    """Short query for stock photo/video search (fewer words rank better)."""
    words = []
    for keyword in visual_keywords(scene_text, topic, limit=3):
        for word in str(keyword).split():
            if word not in words:
                words.append(word)
            if len(words) >= max_words:
                return " ".join(words)
    return " ".join(words)
