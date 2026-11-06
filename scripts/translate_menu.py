#!/usr/bin/env python3
"""Apply reviewed exact UI translations to the user's English localization ZIP.

Usage: python3 scripts/translate_menu.py deadlock_english_localization.zip
The result is a standalone, incomplete localization file under data/.
"""
import argparse
import re
import zipfile
from pathlib import Path

SOURCE = 'resource/localization/citadel_main/citadel_main_english.txt'
TRANSLATIONS = {
    'OK': 'تأیید', 'Cancel': 'لغو', 'Close': 'بستن', 'Ignore': 'نادیده گرفتن',
    "Don't show again": 'دیگر نمایش نده', "Don't show this again": 'دیگر این پیام را نمایش نده',
    'Early Development Build': 'نسخه در مراحل اولیه توسعه', 'Loading...': 'در حال بارگذاری...',
    'Friend Request Pending': 'درخواست دوستی در انتظار پاسخ', 'Friend Request Sent': 'درخواست دوستی ارسال شد',
    'Not friends': 'دوست نیستید', 'Online': 'آنلاین', 'Busy': 'مشغول', 'Away': 'دور از سیستم',
    'Snooze': 'غیرفعال', 'Looking To Trade': 'به دنبال معامله', 'Looking To Play': 'به دنبال بازی',
    'Playing Other Game': 'در حال انجام بازی دیگر', 'Match Ready': 'مسابقه آماده است',
    'Your game has started.': 'بازی شما آغاز شده است.', 'Disconnected from Server': 'اتصال به سرور قطع شد',
    'Disconnected': 'اتصال قطع شد', 'Connection lost': 'ارتباط قطع شد', 'Connection closing': 'در حال بستن اتصال',
    'Kicked by server admin': 'توسط مدیر سرور اخراج شدید', 'Added to banned list': 'به فهرست محرومان اضافه شد',
    'Kicked and banned': 'اخراج و محروم شدید', 'No Steam logon': 'به استیم وارد نشده‌اید',
    'Match does not allow spectators': 'این مسابقه تماشاگر نمی‌پذیرد',
    'Disconnect by user': 'قطع اتصال توسط کاربر', 'Disconnect by server': 'قطع اتصال توسط سرور',
    'Connection rejected by game': 'اتصال توسط بازی رد شد', 'Server version is not compatible.': 'نسخه سرور سازگار نیست.',
    'Replay is not compatible.': 'بازپخش سازگار نیست.', 'Replay not yet ready for download': 'بازپخش هنوز برای دانلود آماده نیست',
    'Replay failed to write to local disk': 'ذخیره بازپخش روی دیسک ناموفق بود',
    'Please wait': 'لطفاً صبر کنید', 'Please Wait': 'لطفاً صبر کنید', 'Error': 'خطا',
    'Healing': 'درمان', 'Melee': 'ضربه نزدیک', 'Kills': 'کشتن‌ها', 'Kill': 'کشتن',
    'Street Brawl': 'نبرد خیابانی', 'Street Brawl (Bots)': 'نبرد خیابانی (بات‌ها)',
    'Patron': 'پاترون', 'Abilities': 'توانایی‌ها', 'Low': 'کم', 'High': 'زیاد',
    'Items': 'آیتم‌ها', 'All': 'همه', 'Ranked': 'رتبه‌ای', 'Heroes': 'قهرمانان',
    'Awful': 'خیلی بد', 'Great': 'عالی', 'Change Hero': 'تغییر قهرمان', 'None': 'هیچ‌کدام',
    'Skill Rating': 'امتیاز مهارت', 'Soul Urn': 'کوزه روح', 'Souls': 'روح‌ها',
    'Hero Labs': 'آزمایشگاه قهرمانان', 'Active': 'فعال', 'Player': 'بازیکن',
    'Base Guardians': 'نگهبانان پایگاه', 'Haunts': 'ارواح', 'Troopers': 'سربازان',
    'Teleport': 'انتقال', 'Jump': 'پرش', 'Off': 'خاموش', 'Med': 'متوسط',
    'Disabled': 'غیرفعال', 'Submit Feedback': 'ارسال بازخورد', 'Weapon Damage': 'آسیب سلاح',
    'Spirit Power': 'قدرت روح', 'Fire Rate': 'سرعت شلیک', 'Movement': 'حرکت', 'Spirit': 'روح',
    'Builds': 'بیلدها', 'Popular Items': 'آیتم‌های محبوب', 'Recommended': 'پیشنهادی',
    'Party': 'گروه', 'Overview': 'نمای کلی', 'Next': 'بعدی', 'Guardian': 'نگهبان',
    'Walker': 'واکر', 'Shrine': 'زیارتگاه', 'Locked': 'قفل‌شده', 'Success': 'موفقیت',
    'Objectives': 'اهداف', 'Scoreboard': 'جدول امتیازات', 'New': 'جدید', 'Parry': 'دفع ضربه',
    'Dash': 'جهش', 'Options': 'گزینه‌ها', 'Base settings': 'تنظیمات پایه', 'Shop': 'فروشگاه',
    'Reset': 'بازنشانی', 'Ultra': 'فوق‌العاده', 'Shoot': 'شلیک', 'Win': 'پیروزی',
    'South America': 'آمریکای جنوبی', 'North America': 'آمریکای شمالی', 'Europe': 'اروپا', 'Oceania': 'اقیانوسیه',
    'Boons': 'موهبت‌ها', 'Boon': 'موهبت', 'Ability Unlock': 'باز کردن توانایی', 'Spirit Damage': 'آسیب روح',
    'Base': 'پایگاه', 'Weapon Items': 'آیتم‌های سلاح', 'Spirit Items': 'آیتم‌های روح',
    'Vitality Items': 'آیتم‌های حیات', 'Wins': 'پیروزی‌ها', 'Back': 'بازگشت', 'Play': 'بازی',
    'Start Match': 'شروع مسابقه', 'Unassigned': 'تعیین‌نشده', 'Invite Friends': 'دعوت دوستان',
    'Ready Up': 'آماده شدن', 'Spectator': 'تماشاگر', 'Join Party': 'پیوستن به گروه',
    'Match Cancelled': 'مسابقه لغو شد', 'Invite': 'دعوت', 'Leave Party': 'ترک گروه',
    'Level Up': 'افزایش سطح', 'Guardians': 'نگهبانان', 'Walkers': 'واکرها', 'Selected': 'انتخاب‌شده',
    'Enemy Patron': 'پاترون دشمن', 'Hidden King': 'پادشاه پنهان', 'Archmother': 'مادر اعظم',
    'Deaths': 'مرگ‌ها', 'Bot Match': 'مسابقه با بات‌ها', 'Browse Builds': 'مرور بیلدها',
    'Damage': 'آسیب', 'Slide': 'سر خوردن', 'Movement Abilities Disabled': 'توانایی‌های حرکتی غیرفعال‌اند',
    'Keybinds': 'کلیدهای کنترل', 'Allies': 'متحدان', 'Pings': 'پینگ‌ها', 'All heroes': 'همه قهرمانان',
    'Reticle': 'نشانگر هدف‌گیری', 'Reload': 'خشاب‌گذاری', 'Careful': 'مراقب باشید',
    'Stay Together': 'کنار هم بمانید', 'Vote': 'رأی', 'Rejected.': 'رد شد.',
    'Successfully submitted': 'با موفقیت ارسال شد', 'Enter': 'ورود', 'Major Update': 'به‌روزرسانی بزرگ',
    'Other': 'سایر', 'Submit': 'ارسال', 'Email:': 'ایمیل:', 'Email Address': 'نشانی ایمیل',
    'Comments:': 'توضیحات:', 'Griefing': 'خرابکاری', 'Smurfing': 'بازی با حساب فرعی',
    'Cheating': 'تقلب', 'Skip Tutorial': 'رد کردن آموزش', 'Loss': 'شکست', 'Not Scored': 'بدون امتیاز',
    'Paused': 'متوقف‌شده', 'Critical': 'بحرانی', 'DPS': 'آسیب در ثانیه', 'Duration': 'مدت',
    'Auto-purchase items': 'خرید خودکار آیتم‌ها', 'Quick Buy': 'خرید سریع', 'Item Purchased': 'آیتم خریداری شد',
    'Bullet Velocity': 'سرعت گلوله', 'Anti-Healing': 'ضد درمان', 'Ability Range': 'برد توانایی',
    'Crowd Control': 'کنترل جمعیت', 'Base Health': 'جان پایه', 'Stat Increases': 'افزایش مشخصات',
    'Bullet Resist': 'مقاومت گلوله', 'Spirit Resist': 'مقاومت روح', 'Owned': 'دارای این آیتم',
}

# Preserve the raw escaped value and every non-value byte, including CRLF/BOM.
ENTRY = re.compile(r'^(\s*"([^"\r\n]+)"[ \t]+")((?:\\.|[^"\r\n])*)("[^\r\n]*\r?)$', re.M)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zipfile', type=Path)
    parser.add_argument('--output', type=Path, default=Path('data/citadel_main_english.txt'))
    args = parser.parse_args()
    with zipfile.ZipFile(args.zipfile) as z:
        raw = z.read(SOURCE)
    text = raw.decode('utf-8')
    count = 0
    def replace(m):
        nonlocal count
        replacement = TRANSLATIONS.get(m.group(3))
        if replacement is None:
            return m.group(0)
        count += 1
        return m.group(1) + '\u200f' + replacement + m.group(4)
    result = ENTRY.sub(replace, text).encode('utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f'Translated {count} entries; saved {args.output}. Other entries remain English.')


if __name__ == '__main__':
    main()
