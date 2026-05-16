# DartPixiv (PixivUtil2 ported to Dart)

A Dart port of [PixivUtil2](https://github.com/Nandaka/PixivUtil2) — a tool
for downloading images, novels, and FANBOX/Sketch posts from
[pixiv.net](https://www.pixiv.net).

The original project is written in Python; this fork rewrites the entire
codebase in Dart so it can run as a single self-contained native binary
(no Python interpreter, no package install) and so the same code can be
embedded inside a future Flutter UI.

## Layout

```
.
├── bin/
│   └── pixiv_util2.dart           # CLI entry point
├── lib/
│   ├── pixiv_util2.dart           # Public library exports
│   ├── pixiv_db_manager.dart      # SQLite database manager
│   ├── pixiv_util_gui.dart        # Stub for a future Flutter GUI
│   ├── common/
│   │   ├── datetime_z.dart        # ISO-8601 / duration parsing helpers
│   │   ├── pixiv_browser.dart     # HTTP client + Pixiv web/AJAX endpoints
│   │   ├── pixiv_config.dart      # config.ini reader/writer
│   │   ├── pixiv_constant.dart    # Version, return codes, HTML template
│   │   ├── pixiv_exception.dart   # Domain exceptions
│   │   ├── pixiv_helper.dart      # Filename/log/utility helpers
│   │   ├── pixiv_oauth.dart       # OAuth refresh-token flow
│   │   └── pixiv_oauth_browser.dart  # PKCE-based OAuth login flow
│   ├── handler/
│   │   ├── pixiv_artist_handler.dart
│   │   ├── pixiv_batch_handler.dart
│   │   ├── pixiv_bookmark_handler.dart
│   │   ├── pixiv_download_handler.dart
│   │   ├── pixiv_fanbox_handler.dart
│   │   ├── pixiv_image_handler.dart
│   │   ├── pixiv_list_handler.dart
│   │   ├── pixiv_novel_handler.dart
│   │   ├── pixiv_ranking_handler.dart
│   │   ├── pixiv_sketch_handler.dart
│   │   └── pixiv_tags_handler.dart
│   └── model/
│       ├── pixiv_artist.dart
│       ├── pixiv_bookmark.dart
│       ├── pixiv_group.dart
│       ├── pixiv_image.dart
│       ├── pixiv_list_item.dart
│       ├── pixiv_model_fanbox.dart
│       ├── pixiv_model_sketch.dart
│       ├── pixiv_novel.dart
│       ├── pixiv_ranking.dart
│       └── pixiv_tags.dart
└── test/
    ├── datetime_z_test.dart
    ├── pixiv_helper_test.dart
    └── pixiv_model_test.dart
```

## Requirements

- Dart SDK 3.4 or newer (download from <https://dart.dev/get-dart>)

## Install dependencies

```sh
dart pub get
```

## Run the CLI

Interactive mode (presents the same menu as the original Python tool):

```sh
dart run bin/pixiv_util2.dart
```

Non-interactive mode (one option at a time, useful for scripting):

```sh
dart run bin/pixiv_util2.dart --option 2 --image-id 12345
dart run bin/pixiv_util2.dart --option 1 --member-id 12345
dart run bin/pixiv_util2.dart --option 3 --tag "風景"
dart run bin/pixiv_util2.dart --option 6 --mode daily --start-page 1 --end-page 3
```

Options:

| `--option` | Operation                       |
| ---------- | ------------------------------- |
| `1`        | Download by Member ID           |
| `2`        | Download by Image ID            |
| `3`        | Download by Tag                 |
| `4`        | Download from list.txt          |
| `5`        | Download bookmarks              |
| `6`        | Download Pixiv ranking          |
| `7`        | Download a single novel         |
| `8`        | Download a novel series         |
| `9`        | Download a Pixiv Sketch artist  |
| `10`       | Download a FANBOX artist        |
| `11`       | Run a `batch_job.json`          |

## Build a standalone binary

```sh
dart compile exe bin/pixiv_util2.dart -o pixiv_util2
./pixiv_util2 --help
```

Windows (PowerShell):

```powershell
dart compile exe .\bin\pixiv_util2.dart -o .\pixiv_util2.exe
.\pixiv_util2.exe --help
```

## Windows quick start

1. Install Dart SDK from <https://dart.dev/get-dart>.
2. Open **PowerShell** in the repository folder.
3. Run:

```powershell
dart pub get
dart run .\bin\pixiv_util2.dart
```

For non-interactive usage:

```powershell
dart run .\bin\pixiv_util2.dart --option 2 --image-id 12345
```

If you use Japanese tags in terminal arguments, switch your shell to UTF-8 first:

```powershell
chcp 65001
```

## Configuration

On first run a `config.ini` will be written with sensible defaults. Open
it in any text editor and fill in your `cookie`, `refresh_token`, output
directory (`rootDirectory`), and any naming format you prefer. The same
keys and sections from the Python version are recognised — see
[lib/common/pixiv_config.dart](lib/common/pixiv_config.dart) for the
full list.

For artwork downloads, make sure the `[Authentication]` section has a
valid Pixiv web cookie. The minimum useful value is usually your
`PHPSESSID`, but pasting `PHPSESSID=...` or a browser `Cookie:` header also
works:

```ini
[Authentication]
cookie = your_pixiv_session_here
```

By default, each artwork is saved into a folder named only after the image ID:

```text
image_id/
  original_image_file.jpg
```

Text info files are disabled by default. Artwork metadata is stored in the
SQLite database table `pixiv_download_metadata`, with image ID, title,
caption, up to ten tags, page count, date, total views, total rating, and
bookmark count. If you already have an older `config.ini`, set
`writeImageInfo = false` and update these filename settings:

```ini
filenameFormat = %image_id%\%urlFilename%
filenameMangaFormat = %image_id%\%urlFilename%
filenameInfoFormat = %image_id%\info
filenameMangaInfoFormat = %image_id%\info
```

## Tests

```sh
dart test
```

## Notes about the port

- File and identifier names follow Dart conventions
  (`snake_case.dart`, `lowerCamelCase` getters, `PascalCase` types).
- Network access uses the standard Dart `http` package together with a
  `cookie_jar` for session cookies, replacing Python's `mechanize`.
- The SQLite layer uses the [`sqlite3`](https://pub.dev/packages/sqlite3)
  package and ports the original schema (members, images, manga pages,
  tags, translations, AI metadata, series, FANBOX posts, Sketch posts).
- HTML parsing uses [`html`](https://pub.dev/packages/html), replacing
  BeautifulSoup. Datetime parsing is in `lib/common/datetime_z.dart`.
- Logging is done with [`logging`](https://pub.dev/packages/logging)
  + ANSI escape codes (replacing Python's `colorama`).
- The original Tk-based GUI in `PixivUtilGUI.py` is intentionally a
  stub (`lib/pixiv_util_gui.dart`); add a Flutter app that imports
  this library to build a desktop UI.

## License

MIT — same as upstream PixivUtil2. See [LICENSE](LICENSE).
