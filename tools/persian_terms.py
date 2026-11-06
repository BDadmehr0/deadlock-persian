"""Translate visible English game terminology in existing Persian VPK strings.

Do not touch markup, placeholders or escape sequences: Valve resolves those at
runtime. Longer phrases take precedence over their individual words.
"""
import re

TERMS = {
    'spirit damage over time': 'آسیب روح در طول زمان',
    'bullet and spirit resist': 'مقاومت گلوله و روح',
    'weapon damage': 'آسیب سلاح', 'spirit damage': 'آسیب روح',
    'bullet damage': 'آسیب گلوله', 'melee damage': 'آسیب ضربه نزدیک',
    'spirit power': 'قدرت روح', 'spirit resistance': 'مقاومت روح',
    'spirit resist': 'مقاومت روح', 'bullet resist': 'مقاومت گلوله',
    'bullet resistance': 'مقاومت گلوله', 'spirit lifesteal': 'سرقت جان با روح',
    'bullet lifesteal': 'سرقت جان با گلوله', 'melee lifesteal': 'سرقت جان با ضربه نزدیک',
    'movement slow': 'کندی حرکت', 'move speed': 'سرعت حرکت',
    'movement speed': 'سرعت حرکت', 'sprint speed': 'سرعت دویدن',
    'fire rate': 'سرعت شلیک', 'max health': 'حداکثر جان', 'max hp': 'حداکثر جان',
    'light melee': 'ضربه نزدیک سبک', 'heavy melee': 'ضربه نزدیک سنگین',
    'melee attack': 'حمله نزدیک', 'healing reduction': 'کاهش درمان',
    'cooldown reduction': 'کاهش زمان بازیابی', 'health regen': 'بازسازی جان',
    'dash jump': 'پرش جهشی', 'dash-jump': 'پرش جهشی', 'alt-cast': 'اجرای جایگزین',
    'love bites': 'گازهای عاشقانه', 'tag along': 'همراهی', 'ground strike': 'ضربه زمینی',
    'ice path': 'مسیر یخی', 'arctic beam': 'پرتو قطبی', 'frozen shelter': 'پناهگاه یخ‌زده',
    'exploding uppercut': 'آپرکات انفجاری', 'sticky bomb': 'بمب چسبان', 'grapple arm': 'بازوی قلاب‌دار',
    'flying cloak': 'شنل پرنده', 'serrated knives': 'چاقوهای دندانه‌دار',
    'killing blow': 'ضربه کشنده', 'fissure wall': 'دیوار شکاف',
    'potent vapors': 'بخارهای قوی', 'rat king': 'شاه موش‌ها', 'combat barrier': 'مانع نبرد',
    'time-stop': 'توقف زمان', 'bounce pad': 'سکوی پرش', 'bio blast': 'انفجار زیستی',
    'concussive combustion': 'احتراق کوبنده', 'fairfax industries': 'صنایع فیرفکس',
    'cooling down': 'در حال بازیابی', 'overheating': 'گرمای بیش از حد',
    'overheat': 'داغ شدن بیش از حد', 'of dead': 'مردگان',
    'hero': 'قهرمان', 'heroes': 'قهرمانان', 'minion': 'سرباز', 'npc': 'شخصیت غیرقابل‌بازی',
    'souls': 'روح‌ها', 'soul': 'روح', 'secure': 'تأیید', 'deny': 'انکار',
    'damage': 'آسیب', 'spirit': 'روح', 'stun': 'گیجی', 'melee': 'ضربه نزدیک',
    'slow': 'کندی', 'slowing': 'کندکننده', 'resistance': 'مقاومت', 'resist': 'مقاومت',
    'bullet': 'گلوله', 'cooldown': 'زمان بازیابی', 'speed': 'سرعت', 'move': 'حرکت',
    'movement': 'حرکت', 'silence': 'سکوت', 'health': 'جان', 'healing': 'درمان',
    'heal': 'درمان', 'fire': 'شلیک', 'rate': 'نرخ', 'weapon': 'سلاح',
    'debuff': 'اثر منفی', 'buff': 'اثر مثبت', 'stack': 'انباشت', 'stacks': 'انباشت‌ها',
    'power': 'قدرت', 'barrier': 'مانع', 'stamina': 'استقامت', 'dash': 'جهش',
    'passive': 'غیرفعال', 'active': 'فعال', 'lifesteal': 'سرقت جان',
    'light': 'سبک', 'heavy': 'سنگین', 'reload': 'خشاب‌گذاری', 'air': 'هوا',
    'disarm': 'خلع سلاح', 'sleep': 'خواب', 'reduction': 'کاهش', 'rage': 'خشم',
    'ultimate': 'توانایی نهایی', 'parry': 'دفع ضربه', 'mark': 'علامت', 'deadhead': 'ددهد',
    'sprint': 'دویدن', 'kill': 'کشتن', 'shot': 'شلیک', 'curse': 'نفرین', 'jump': 'پرش',
    'teleport': 'انتقال', 'max': 'حداکثر', 'proc': 'فعال‌سازی', 'headshot': 'هدشات',
    'ammo': 'مهمات', 'cast': 'اجرا', 'regen': 'بازسازی', 'respawn': 'بازگشت',
    'immobilize': 'بی‌حرکتی', 'immobilized': 'بی‌حرکت‌شده', 'unlock': 'باز کردن',
    'execute': 'ضربه نهایی', 'shock': 'شوک', 'attack': 'حمله', 'multi': 'چندگانه',
    'bonus': 'اضافی', 'hex': 'طلسم', 'assist': 'کمک', 'aura': 'هاله', 'chain': 'زنجیره',
    'unstoppable': 'توقف‌ناپذیر', 'invisible': 'نامرئی', 'invisibility': 'نامرئی بودن',
    'napalm': 'ناپالم', 'afterburn': 'پس‌سوز', 'ground': 'زمین', 'strike': 'ضربه',
    'invulnerable': 'آسیب‌ناپذیر', 'invincible': 'شکست‌ناپذیر', 'bounce': 'جهش', 'pad': 'سکو',
    'ava': 'آوا', 'charged': 'شارژشده', 'armor': 'زره', 'djinn': 'جن',
    'wrecked': 'درهم‌شکسته', 'ram': 'یورش', 'deflect': 'انحراف', 'rat': 'موش',
    'king': 'شاه', 'bishop': 'فیل', 'rook': 'رخ', 'queen': 'وزیر',
    'crit': 'ضربه بحرانی', 'splitshot': 'شلیک چندگانه', 'amp': 'تقویت', 'freeze': 'انجماد',
    'mystic': 'جادویی', 'decay': 'فرسایش', 'root': 'ریشه', 'boon': 'موهبت',
    'ricochet': 'کمانه', 'jumping': 'پرش', 'dazed': 'گیج‌شده', 'cleanse': 'پاک‌سازی',
    'chained': 'زنجیرشده', 'sliding': 'سر خوردن', 'void': 'خلأ', 'charmed': 'افسون‌شده',
    'joker': 'جوکر', 'dagger': 'خنجر', 'perfect': 'بی‌نقص', 'accuracy': 'دقت',
    'singularity': 'تکینگی', 'stasis': 'ایستایی', 'salvaged': 'بازیافت‌شده',
    'uppercut': 'آپرکات', 'bomb': 'بمب', 'grapple': 'قلاب', 'fading': 'کاهشی',
    'crackshot': 'تیرانداز ماهر', 'lasso': 'کمند', 'pounce': 'خیز',
    'multishot': 'شلیک چندگانه', 'malice': 'بدخواهی', 'assassinate': 'ترور',
    'shield': 'سپر', 'bleed': 'خونریزی', 'shiv': 'شیو', 'airdash': 'جهش هوایی',
    'barrage': 'رگبار', 'knock': 'ضربه', 'traveler': 'مسافر', 'outgoing': 'خروجی',
    'double': 'دوگانه', 'slide': 'سر خوردن', 'petrify': 'سنگ کردن', 'petrified': 'سنگ‌شده',
    'untargetable': 'غیرقابل‌هدف‌گیری', 'hexed': 'طلسم‌شده', 'fear': 'ترس',
    'stalker': 'تعقیب‌گر', 'ambush': 'کمین', 'isolated': 'جداافتاده', 'jar': 'ظرف',
    'innate': 'ذاتی', 'wither': 'پژمردگی', 'lycan': 'گرگینه', 'human': 'انسان',
    'wolf': 'گرگ', 'blessed': 'متبرک', 'reveal': 'آشکارسازی', 'distance': 'فاصله',
    'luminous': 'درخشان', 'cap': 'سقف', 'swarm': 'انبوه', 'threadsap': 'مکیدن رشته',
    'knight': 'شوالیه', 'battery': 'باتری', 'backblast': 'پس‌انفجار',
    'empower': 'تقویت', 'draw': 'نقاشی', 'sketch': 'طرح', 'chimera': 'کیمرا',
}

# VPK strings use escaped quotes in HTML attributes. Never translate inside
# markup, interpolation tokens, or escape sequences such as \\n and \\".
PROTECTED = re.compile(r'(<[^>]*>|\{[^{}]*\}|\\.)')
PATTERN = re.compile(
    r'(?<![A-Za-z])(?:' + '|'.join(
        re.escape(term).replace(r'\ ', r'[ \u00a0]+')
        for term in sorted(TERMS, key=len, reverse=True)
    ) + r')(?![A-Za-z])', re.IGNORECASE,
)


# Contextual corrections for common inflections after terminology replacement.
PERSIAN_CORRECTIONS = {
    'روح ای': 'روحی',
    'گیجی کرده': 'گیج کرده',
    'گیجی کردن': 'گیج کردن',
    'گیجی می‌شود': 'گیج می‌شود',
    'گیجی می‌شوید': 'گیج می‌شوید',
    'کندکننده\u00a0طلسم': 'طلسم کندکننده',
}


def translate_visible_terms(value):
    def replace(match):
        key = re.sub(r'[ \u00a0]+', ' ', match.group().lower())
        return TERMS[key]
    parts = PROTECTED.split(value)
    for i in range(0, len(parts), 2):
        parts[i] = PATTERN.sub(replace, parts[i])
        for old, new in PERSIAN_CORRECTIONS.items():
            parts[i] = parts[i].replace(old, new)
    return ''.join(parts)
