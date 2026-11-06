# فارسی‌ساز Deadlock

> ترجمهٔ منو هنوز کامل نیست و سازگاری فایل‌ها داخل بازی آزمایش نشده است. پیش از نصب بازی را ببندید.

## نصب و به‌روزرسانی تک‌خطی

> این فرمان‌ها به شاخهٔ `arena/435414a8-deadlock-persian` اشاره دارند و فقط پس از انتشار اسکریپت‌های جدید روی آن شاخه کار می‌کنند. در صورت حذف شاخه باید آدرس‌ها و مرجع شاخه در اسکریپت‌ها به یک شاخهٔ منتشرشده تغییر کنند. قبل از اجرای کد دانلودشده، محتوای آن را بررسی کنید.

بازی را ببندید. در لینوکس به Bash، Git، Python 3 و curl نیاز است. در ویندوز Git for Windows و Python 3 همراه Python Launcher (`py -3`) را نصب کنید و از PowerShell استفاده کنید. سازگاری در ویندوز و داخل بازی هنوز آزمایش نشده است.

### لینوکس (Bash)

نصب:
```bash
set -o pipefail; curl -fsSL https://raw.githubusercontent.com/BDadmehr0/deadlock-persian/arena/435414a8-deadlock-persian/scripts/bootstrap.sh | bash -s -- install
```
به‌روزرسانی نصب موجود:
```bash
set -o pipefail; curl -fsSL https://raw.githubusercontent.com/BDadmehr0/deadlock-persian/arena/435414a8-deadlock-persian/scripts/bootstrap.sh | bash -s -- update
```
اگر محل بازی متفاوت است، بعد از `install` یا `update` مسیر پوشهٔ citadel را در کوتیشن اضافه کنید: `"/path/to/Deadlock/game/citadel"`.

### ویندوز (PowerShell)

نصب:
```powershell
& ([scriptblock]::Create((Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/BDadmehr0/deadlock-persian/arena/435414a8-deadlock-persian/scripts/bootstrap.ps1').Content)) -Action install
```
به‌روزرسانی نصب موجود:
```powershell
& ([scriptblock]::Create((Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/BDadmehr0/deadlock-persian/arena/435414a8-deadlock-persian/scripts/bootstrap.ps1').Content)) -Action update
```
نصاب سعی می‌کند بازی را در کتابخانه‌های Steam پیدا کند؛ در صورت نیاز `-GameDir "C:\path\to\Deadlock\game\citadel"` را به انتهای دستور اضافه کنید. برای حذف و بازیابی فایل‌های اصلی:
```powershell
py -3 "$env:LOCALAPPDATA\DeadlockPersian\scripts\install_windows.py" uninstall
```
در صورت نیاز، `--game-dir "C:\path\to\Deadlock\game\citadel"` را اضافه کنید. برای بازنویسی فایل‌هایی که پس از نصب تغییر کرده‌اند، فقط پس از بررسی و آگاهی از حذف تغییرات بعدی، از `--force` استفاده کنید.

نصاب‌ها فایل‌های اصلی را در `.deadlock-persian-backup` نگه می‌دارند و در صورت تغییر فایل‌های نصب‌شده، به‌روزرسانی و حذف را متوقف می‌کنند. checkout نصب در لینوکس در `${XDG_DATA_HOME:-$HOME/.local/share}/deadlock-persian` و در ویندوز در `%LOCALAPPDATA%\DeadlockPersian` قرار می‌گیرد؛ تغییرات محلی checkout مانع به‌روزرسانی خودکار می‌شوند.

## نصب و حذف

در ریشهٔ پروژه، منوی ترمینالی را اجرا کنید:

```bash
bash manage.sh
```

مسیر پیش‌فرض بازی `~/.local/share/Steam/steamapps/common/Deadlock/game/citadel` است. اگر بازی جای دیگری نصب شده، مسیر پوشهٔ `citadel` را بدهید:

```bash
bash manage.sh "/path/to/Deadlock/game/citadel"
```

همچنین می‌توانید مستقیماً از `bash install.sh [مسیر بازی]` و `bash uninstall.sh [مسیر بازی]` استفاده کنید. نصب به Python 3 نیاز دارد.

نصاب ابتدا یک نسخهٔ موقت از `data/pak82_dir.vpk` را با `tools/translate_common.py` آماده می‌کند و آن را همراه `data/citadel_main_english.txt` نصب می‌کند. فایل‌های اصلی در پوشهٔ `.deadlock-persian-backup` داخل پوشهٔ بازی ذخیره می‌شوند. حذف ترجمه، نسخه‌های اصلی را برمی‌گرداند؛ اگر فایلی قبل از نصب وجود نداشته، آن را حذف می‌کند.

اگر فایل‌های نصب‌شده بعداً تغییر کنند، مثلاً با به‌روزرسانی بازی، حذف‌کننده برای جلوگیری از بازنویسی متوقف می‌شود. پس از بررسی فایل‌ها، در صورت تمایل به بازگرداندن نسخهٔ پشتیبان اولیه می‌توانید `bash uninstall.sh --force [مسیر بازی]` را اجرا کنید. این کار تغییرات بعدی آن دو فایل را بازنویسی می‌کند.

## بازسازی ترجمه

- `python3 tools/translate_common.py` فایل `data/pak82_dir.vpk` را به‌روز می‌کند؛ می‌توان مسیر یک نسخهٔ دیگر را نیز به‌عنوان آرگومان داد.
- `python3 scripts/translate_menu.py deadlock_english_localization.zip` فایل `data/citadel_main_english.txt` را از بستهٔ فایل‌های انگلیسی بازسازی می‌کند. عبارت‌هایی که هنوز ترجمه نشده‌اند انگلیسی باقی می‌مانند.

## فایل‌های محلی توسعه

کش‌های Python، فایل‌های موقت نصب و گزارش محلی `deadlock_vpk_report.txt` در `.gitignore` قرار دارند. بخش‌های VPK که از بازی استخراج یا بازسازی می‌شوند نیز به‌طور پیش‌فرض نادیده گرفته می‌شوند؛ فایل‌هایی که از قبل در مخزن ثبت شده‌اند همچنان تحت کنترل نسخه باقی می‌مانند. فایل ترجمهٔ موردنیاز نصب یعنی `data/pak82_dir.vpk` نادیده گرفته نمی‌شود.
