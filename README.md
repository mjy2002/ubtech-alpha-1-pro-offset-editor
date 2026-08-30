# UBTECH Alpha 1 Pro Offset Editor

Standalone Windows GUI for reading and writing EEPROM servo offsets on UBTECH Alpha 1 Pro / Alpha 1S robots over USB HID.

The editor shows the original AlphaRobot joint map, reads all 16 servo offsets, lets you adjust values by one degree, and creates a JSON backup before the first write.

Maintained by Maslodium.

## Hardware

- Robot: UBTECH Alpha 1 Pro / Alpha 1S.
- USB device: HID `VID 0483 / PID 5750`, product `Alpha1`.
- No COM port is required for the stock USB connection.

Close `AlphaRobot1s_QT` before using this editor, because only one program can talk to the robot over HID at a time.

## Run From Source

```powershell
python -m pip install --user -r requirements.txt
python .\alpha_offset_editor.py
```

Or double-click:

```text
run_alpha_offset_editor.cmd
```

To check communication without opening the GUI or writing anything:

```powershell
python .\alpha_offset_editor.py --check
```

## Files

- `alpha_offset_editor.py` - Tkinter GUI editor.
- `alpha_joint_map.png` - original AlphaRobot joint map used by the editor.
- `run_alpha_offset_editor.cmd` - Windows launcher.
- `docs/Alpha1s.xml` - servo profile from the stock AlphaRobot software.
- `docs/README-alpha-offset-editor.md` - Russian usage notes.
- `docs/README-alpha-servo-id.md` - notes about the experimental servo ID sketch that is not included in this source package.

## Safety

The editor writes absolute EEPROM offsets. Use small changes, support the robot mechanically, and verify the result after each write. The generated `alpha-offsets-backup-*.json` files are ignored by git because they contain device-specific calibration data.

---

# Редактор оффсетов UBTECH Alpha 1 Pro

Отдельная Windows-утилита для чтения и записи EEPROM-оффсетов сервоприводов UBTECH Alpha 1 Pro / Alpha 1S через USB HID.

Редактор показывает оригинальную карту суставов AlphaRobot, считывает все 16 оффсетов, позволяет менять значения с шагом в один градус и перед первой записью создаёт JSON-бэкап.

Поддерживает Maslodium.

## Оборудование

- Робот: UBTECH Alpha 1 Pro / Alpha 1S.
- USB-устройство: HID `VID 0483 / PID 5750`, product `Alpha1`.
- Для штатного USB-подключения COM-порт не нужен.

Перед запуском закройте `AlphaRobot1s_QT`: одновременно с роботом по HID может работать только одна программа.

## Запуск из исходников

```powershell
python -m pip install --user -r requirements.txt
python .\alpha_offset_editor.py
```

Или двойным кликом:

```text
run_alpha_offset_editor.cmd
```

Проверка связи без открытия GUI и без записи:

```powershell
python .\alpha_offset_editor.py --check
```

## Файлы

- `alpha_offset_editor.py` - GUI-редактор на Tkinter.
- `alpha_joint_map.png` - оригинальная карта суставов AlphaRobot.
- `run_alpha_offset_editor.cmd` - Windows-запускатель.
- `docs/Alpha1s.xml` - профиль сервоприводов из штатного AlphaRobot.
- `docs/README-alpha-offset-editor.md` - заметки по использованию на русском.
- `docs/README-alpha-servo-id.md` - заметки про экспериментальный скетч определения ID сервопривода, не входящий в пакет исходников.

## Безопасность

Редактор записывает абсолютные EEPROM-оффсеты. Меняйте значения небольшими шагами, поддерживайте робота механически и проверяйте результат после каждой записи. Файлы `alpha-offsets-backup-*.json` игнорируются git, потому что содержат калибровку конкретного устройства.
