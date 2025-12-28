# PixivUtil2 v20251112 - Custom Modifications

## Overview
This document describes the modifications made to PixivUtil2 v20251112 to enhance preheat functionality, support member sorting by download count, and add features for marking completed authors.

## Key Features Added

### 1. Preheat Checkpoint and Resume Support
**Files Modified:** `handler/PixivBookmarkHandler.py`, `common/PixivHelper.py`

- **Checkpoint/Resume:** Preheat progress is now saved to `<list_file>.preheat_progress.json`, allowing interruption and continuation of member profile fetching.
- **Progress Tracking:** Stores a list of processed member IDs and metadata (timestamp, list file, total count).
- **Resume Logic:** When preheat runs with `resume=True`, it skips already-processed members.
- **Configuration:** 
  - `preheatDelaySeconds` or `preheatDelay` (in config.ini) controls delay between requests (minimum 0.1s).
  - Can be overridden via command line or menu input.

**Implementation Details:**
- Helper functions: `_load_preheat_progress()`, `_save_preheat_progress()`
- Handles interrupts gracefully (Ctrl+C), flushing progress before exit
- Flushes progress periodically (every 10 members by default) to minimize data loss

### 2. Configurable Member Download Order
**Files Modified:** `common/PixivConfig.py`, `handler/PixivBookmarkHandler.py`

- **Config Options Added:**
  - `memberOrder` (Settings section): Controls sort order of followed authors
  - Supported values: `"fewest_first"` (ascending), `"most_first"` (descending), or empty string (no sorting)
  
- **Sorting Logic:** When processing bookmarks/followed artists:
  - Retrieves `total_images` from DB for each member (populated by preheat)
  - Falls back to local image count if total_images is unavailable
  - Members with fewer total images are processed first (fewest_first mode)

**Implementation Details:**
- New function: `_sort_followed_members()` in PixivBookmarkHandler
- Deduplicates member list (keeping first occurrence)
- Compatible with both local DB and fallback image counting

### 3. Total Images Tracking in Database
**Files Modified:** `PixivDBManager.py`

- **Database Schema:** Added `total_images` column to `pixiv_master_member` table
- **Migration:** Automatic column addition via `createDatabase()` if not present
- **Methods Added:**
  - `updateMemberTotalImages(memberId, totalImages)` - Updates or inserts member total
  - `selectMemberTotalImagesMap(member_ids=None)` - Returns `{member_id(int): total_images(int)}` mapping
  
- **Preheat Integration:** During preheat, fetches member profile and stores `artist.totalImages` in DB for future sorting

### 4. Fixed Download Path Generation
**Files Modified:** `handler/PixivBookmarkHandler.py`, `common/PixivHelper.py`

- **Issue Fixed:** Previous behavior forced downloads to old per-member save paths regardless of config
- **Solution:** Modified `process_bookmark()` to pass `user_dir=''` to `process_member()`, allowing `config.filenameFormat` and `config.rootDirectory` to be respected
- **Result:** All downloads now follow configured filename format and root directory

### 5. Floating-Point Delay Support
**Files Modified:** `common/PixivHelper.py`

- **Function:** `print_delay(retry_wait)` now accepts float values (e.g., 0.1, 0.5)
- **Behavior:** Sleeps for precise duration without per-second loop overhead
- **Output:** Single concise status message instead of repeated per-second messages

### 6. Robust JSON Progress File Handling
**Files Modified:** `model/PixivImage.py`

- **Issue Fixed:** `WriteJSON()` could throw KeyError when removing non-existent fields
- **Solution:** Uses `dict.pop(key, None)` for safe field removal
- **Result:** No crashes when JSON structure varies or fields are missing

### 7. Scan and Mark Completed Members
**Files Modified:** `PixivUtil2.py`, `handler/PixivBookmarkHandler.py`

- **New Menu Option:** `5b. Scan local followed artists and mark completed members`
- **Function:** `scan_and_mark_completed_members()` in PixivBookmarkHandler
- **Behavior:**
  - Scans local DB and filesystem for followed members
  - Compares local image count against `total_images` (from DB or optionally remote)
  - Marks members as "complete" and adds them to preheat progress file's `done` list
  - Future preheat/download runs will skip these members
  - Optional `compare_remote` flag fetches remote total_images for verification
  - Optional `dry_run` mode (default: enabled) previews changes without writing

- **Integration:**
  - New menu handler: `menu_scan_and_mark_complete()` in PixivUtil2.py
  - Uses same progress file format as preheat for compatibility
  - Respects `config.rootDirectory` and `config.filenameFormat`

## Configuration Changes

### New Config.ini Entries (Settings section)
```ini
[Settings]
preheatDelaySeconds = 0.1          # Preheat delay in seconds (supports float)
preheatDelay = 0.1                 # Alternative name for preheatDelaySeconds
memberOrder = fewest_first         # Sort followed members: fewest_first, most_first, or empty
rootDirectory = G:\Porn\Pixiv      # Root directory for downloads

[Filename]
filenameFormat = %member_id% %artist%\\%image_id% - %title%\\%image_id% - %title%
```

## Usage Examples

### 1. Preheat with Resume
```bash
python PixivUtil2.py
# Select option: 5a
# Enter list file or press Enter for default
# Preheat fetches member profiles and saves progress
# Press Ctrl+C to interrupt - progress is saved
# Run again and it resumes from where it stopped
```

### 2. Download with Fewest-First Sorting
```bash
# Ensure preheat has populated total_images in DB
# Set memberOrder = fewest_first in config.ini
# Select option: 5 (Download from followed artists)
# Members with fewer total images are downloaded first
```

### 3. Scan and Mark Completed Authors
```bash
python PixivUtil2.py
# Select option: 5b
# Enter list file (or default)
# Choose: compare against remote? (Y/N)
# Choose: dry run? (default Y)
# Review results
# If satisfied, run again with dry_run=n to write progress
```

## Files Modified

| File | Changes |
|------|---------|
| `PixivUtil2.py` | Added menu option `5b` and `menu_scan_and_mark_complete()` handler |
| `handler/PixivBookmarkHandler.py` | Added preheat checkpoint helpers, sorting logic, and `scan_and_mark_completed_members()` |
| `common/PixivConfig.py` | Registered `preheatDelaySeconds`, `preheatDelay`, `memberOrder` config items |
| `common/PixivHelper.py` | Updated `print_delay()` to accept float and simplified delay display |
| `PixivDBManager.py` | Added `total_images` column migration and DB methods for total_images management |
| `model/PixivImage.py` | Fixed `WriteJSON()` to safely remove keys using `pop(key, None)` |

## Backward Compatibility

- **Database:** Automatic schema migration via `createDatabase()`; existing databases are updated on first run
- **Config:** All new config items have sensible defaults; existing config.ini files are compatible
- **API:** No breaking changes to public method signatures
- **Menu:** New options are additions; existing options remain unchanged

## Technical Details

### Preheat Progress File Format
```json
{
  "done": ["123456", "789012", "345678"],
  "updated_at": "2025-12-26 10:30:45",
  "list_file": "followed_artists.txt",
  "total": 1005
}
```

### Database Schema Change
```sql
ALTER TABLE pixiv_master_member ADD COLUMN total_images INTEGER;
```

### Member Sorting Algorithm
1. Fetch `total_images` from DB for each member
2. If unavailable, fall back to local image count
3. Sort by total_images (ascending for fewest_first)
4. Maintain stable sort (preserve original order for ties)

## Known Limitations

- **Remote Comparison:** When `compare_remote=True`, network requests are made for each member without total_images in DB; use `preheatDelaySeconds` to avoid rate limiting
- **Folder Detection:** Completion detection relies on `save_folder` or filename format inference; edge cases may exist with special characters or custom folder structures
- **Progress File:** Large member lists (10,000+) may result in large progress JSON; consider archiving periodically

## Troubleshooting

### Preheat Not Resuming
- Check that `<list_file>.preheat_progress.json` exists and is readable
- Delete or rename progress file to force full re-preheat: `del followed_artists.txt.preheat_progress.json`

### Sorting Not Applied
- Ensure DB has `total_images` populated (run preheat first)
- Check `memberOrder` is set to `fewest_first` or `most_first` in config.ini
- Verify config reloads: press `r` in menu to reload config.ini

### Completed Members Not Marked
- Ensure DB and local downloads are in sync
- Use `dry_run=True` (default) first to preview
- Check `compare_remote=True` if DB lacks total_images for some members

## Future Enhancements

Potential improvements for future versions:
- Batch mark multiple members as complete
- Auto-redownload missing images in completed folders
- Progress bar for scan operation
- Export completion status to external format
- Per-author completion statistics
