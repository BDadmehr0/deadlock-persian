#!/usr/bin/env bash
# Interactive installer / uninstaller. Optional argument: game/citadel directory.
set -u
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
if (( $# > 1 )); then echo "Usage: $0 [path-to-game/citadel]" >&2; exit 2; fi
GAME=${1:-"$HOME/.local/share/Steam/steamapps/common/Deadlock/game/citadel"}
while true; do
    printf '\n%s\n' '=== نصب فارسی‌ساز Deadlock ===' "مسیر بازی: $GAME" \
        '1) نصب یا به‌روزرسانی ترجمه' \
        '2) حذف ترجمه و بازگرداندن فایل‌های اصلی' \
        '3) خروج'
    printf 'انتخاب شما [1-3]: '
    if ! IFS= read -r choice; then printf '\n'; exit 0; fi
    case "$choice" in
        1) if bash "$ROOT/install.sh" "$GAME"; then
               printf '%s\n' 'نصب با موفقیت انجام شد.'
           else
               printf '%s\n' 'نصب ناموفق بود؛ پیام بالا را بررسی کنید.' >&2
           fi ;;
        2) printf '%s' 'فایل‌های اصلی از نسخهٔ پشتیبان بازگردانده شوند؟ [y/N]: '
           if ! IFS= read -r answer; then printf '\n'; exit 0; fi
           case "$answer" in
               [yY]|[yY][eE][sS])
                   if bash "$ROOT/uninstall.sh" "$GAME"; then
                       printf '%s\n' 'حذف ترجمه با موفقیت انجام شد.'
                   else
                       printf '%s\n' 'حذف انجام نشد؛ پیام بالا را بررسی کنید.' >&2
                   fi ;;
               *) printf '%s\n' 'حذف لغو شد.' ;;
           esac ;;
        3|q|Q) exit 0 ;;
        *) printf '%s\n' 'گزینهٔ نامعتبر؛ عدد ۱، ۲ یا ۳ را وارد کنید.' >&2 ;;
    esac
done
