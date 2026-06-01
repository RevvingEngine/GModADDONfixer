"""
GMod Addons Fixer
-----------------
- Распаковывает LZMA-сжатые .bin файлы в .gma
- Переименовывает дубликаты файлов (одинаковые имена в разных папках)
- Выводит статистику в конце

Использование:
    python gmod_addons_fix.py "C:/Path/To/GarrysMod/garrysmod/addons"
"""

import os
import sys
import lzma
import uuid
from collections import defaultdict


LZMA_MAGIC = b'\x5d'  # первый байт LZMA


def is_lzma(path):
    try:
        with open(path, 'rb') as f:
            return f.read(1) == LZMA_MAGIC
    except Exception:
        return False


def decompress_lzma_bin(src_path, dst_path):
    with open(src_path, 'rb') as f:
        data = f.read()
    dec = lzma.decompress(data)
    with open(dst_path, 'wb') as f:
        f.write(dec)


def random_suffix(length=8):
    return uuid.uuid4().hex[:length]


def collect_files(addons_path):
    """Собирает все файлы рекурсивно, возвращает {имя_файла: [полные_пути]}"""
    name_to_paths = defaultdict(list)
    for root, dirs, files in os.walk(addons_path):
        for fname in files:
            full_path = os.path.join(root, fname)
            name_to_paths[fname].append(full_path)
    return name_to_paths


def fix_addons(addons_path):
    print(f"\n{'='*55}")
    print(f"  GMod Addons Fixer")
    print(f"{'='*55}")
    print(f"  Папка: {addons_path}\n")

    if not os.path.isdir(addons_path):
        print(f"[ОШИБКА] Папка не найдена: {addons_path}")
        sys.exit(1)

    # Статистика
    bin_total        = 0   # найдено .bin файлов
    bin_fixed        = 0   # успешно распаковано
    bin_skipped      = 0   # не LZMA — пропущено
    bin_failed       = 0   # ошибка при распаковке
    dup_groups       = 0   # групп дубликатов
    dup_renamed      = 0   # файлов переименовано
    dup_failed       = 0   # не удалось переименовать
    failed_details   = []  # детали ошибок

    # ── 1. Распаковка .bin ──────────────────────────────────────────
    print("[ 1/2 ] Поиск и распаковка .bin файлов...")
    for root, dirs, files in os.walk(addons_path):
        for fname in files:
            if not fname.lower().endswith('.bin'):
                continue
            bin_total += 1
            src = os.path.join(root, fname)

            if not is_lzma(src):
                print(f"  [SKIP]  {src}  (не LZMA)")
                bin_skipped += 1
                continue

            base = os.path.splitext(fname)[0]
            dst = os.path.join(root, base + '.gma')

            # Если .gma уже существует — не перезаписываем
            if os.path.exists(dst):
                print(f"  [SKIP]  {fname}  (уже есть {base}.gma)")
                bin_skipped += 1
                continue

            try:
                decompress_lzma_bin(src, dst)
                print(f"  [OK]    {fname}  →  {base}.gma")
                bin_fixed += 1
            except Exception as e:
                msg = f"{src}: {e}"
                print(f"  [FAIL]  {msg}")
                failed_details.append(('bin', msg))
                bin_failed += 1

    # ── 2. Дубликаты ────────────────────────────────────────────────
    print(f"\n[ 2/2 ] Поиск дубликатов (одинаковые имена в разных папках)...")
    name_to_paths = collect_files(addons_path)

    for fname, paths in name_to_paths.items():
        if len(paths) < 2:
            continue
        dup_groups += 1
        print(f"\n  Дубликат: '{fname}'  ({len(paths)} копии)")

        # Первый файл оставляем как есть, остальные переименовываем
        for path in paths[1:]:
            dirn = os.path.dirname(path)
            ext = os.path.splitext(fname)[1]
            new_name = random_suffix(12) + ext
            new_path = os.path.join(dirn, new_name)

            # На случай коллизии суффикса (крайне маловероятно)
            while os.path.exists(new_path):
                new_name = random_suffix(12) + ext
                new_path = os.path.join(dirn, new_name)

            try:
                os.rename(path, new_path)
                print(f"    [OK]  {path}")
                print(f"       →  {new_path}")
                dup_renamed += 1
            except Exception as e:
                msg = f"{path}: {e}"
                print(f"    [FAIL]  {msg}")
                failed_details.append(('dup', msg))
                dup_failed += 1

    # ── Статистика ───────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  СТАТИСТИКА")
    print(f"{'='*55}")
    print(f"  .bin файлов найдено:        {bin_total}")
    print(f"  .bin распаковано (LZMA):    {bin_fixed}")
    print(f"  .bin пропущено (не LZMA):   {bin_skipped}")
    print(f"  .bin ошибок:                {bin_failed}")
    print(f"  ─────────────────────────────────")
    print(f"  Групп дубликатов:           {dup_groups}")
    print(f"  Файлов переименовано:        {dup_renamed}")
    print(f"  Ошибок переименования:       {dup_failed}")
    total_fixed = bin_fixed + dup_renamed
    total_failed = bin_failed + dup_failed
    print(f"  ─────────────────────────────────")
    print(f"  Всего пофикшено:            {total_fixed}")
    print(f"  Всего ошибок:               {total_failed}")

    if failed_details:
        print(f"\n  Что не удалось исправить:")
        for kind, msg in failed_details:
            tag = '.bin' if kind == 'bin' else 'dup'
            print(f"    [{tag}] {msg}")

    print(f"{'='*55}\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python gmod_addons_fix.py <путь до папки addons>")
        print('Пример: python gmod_addons_fix.py "D:/Games/Garrys Mod/garrysmod/addons"')
        sys.exit(1)

    fix_addons(sys.argv[1])
