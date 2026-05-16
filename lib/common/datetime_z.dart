/// Functions to parse datetime strings, ported from datetime_z.py.
library;

final RegExp _dateRe = RegExp(r'^(\d{4})-(\d{1,2})-(\d{1,2})$');

final RegExp _timeRe = RegExp(
  r'^(\d{1,2}):(\d{1,2})(?::(\d{1,2})(?:\.(\d{1,6})\d{0,6})?)?$',
);

final RegExp _datetimeRe = RegExp(
  r'^(\d{4})-(\d{1,2})-(\d{1,2})'
  r'[T ](\d{1,2}):(\d{1,2})'
  r'(?::(\d{1,2})(?:\.(\d{1,6})\d{0,6})?)?'
  r'(Z|[+-]\d{2}(?::?\d{2})?)?$',
);

/// Parse a date string in `YYYY-MM-DD` form. Returns `null` if not parseable.
DateTime? parseDate(String value) {
  final m = _dateRe.firstMatch(value);
  if (m == null) return null;
  return DateTime(int.parse(m.group(1)!),
      int.parse(m.group(2)!), int.parse(m.group(3)!));
}

/// Parse a time-only string. Returns a DateTime where the date is epoch.
DateTime? parseTime(String value) {
  final m = _timeRe.firstMatch(value);
  if (m == null) return null;
  final hour = int.parse(m.group(1)!);
  final minute = int.parse(m.group(2)!);
  final second = m.group(3) != null ? int.parse(m.group(3)!) : 0;
  var micro = 0;
  if (m.group(4) != null) {
    final padded = m.group(4)!.padRight(6, '0');
    micro = int.parse(padded);
  }
  return DateTime(1970, 1, 1, hour, minute, second, micro ~/ 1000, micro % 1000);
}

/// Parse a datetime string with optional timezone. Returns UTC-converted DateTime.
DateTime? parseDatetime(String value) {
  final m = _datetimeRe.firstMatch(value);
  if (m == null) return null;
  final year = int.parse(m.group(1)!);
  final month = int.parse(m.group(2)!);
  final day = int.parse(m.group(3)!);
  final hour = int.parse(m.group(4)!);
  final minute = int.parse(m.group(5)!);
  final second = m.group(6) != null ? int.parse(m.group(6)!) : 0;
  var micro = 0;
  if (m.group(7) != null) {
    final padded = m.group(7)!.padRight(6, '0');
    micro = int.parse(padded);
  }
  final tz = m.group(8);

  if (tz == null) {
    return DateTime(year, month, day, hour, minute, second,
        micro ~/ 1000, micro % 1000);
  } else if (tz == 'Z') {
    return DateTime.utc(year, month, day, hour, minute, second,
        micro ~/ 1000, micro % 1000);
  } else {
    final sign = tz[0] == '-' ? -1 : 1;
    final cleaned = tz.substring(1).replaceAll(':', '');
    int offsetMinutes = 0;
    if (cleaned.length >= 2) {
      offsetMinutes = int.parse(cleaned.substring(0, 2)) * 60;
      if (cleaned.length >= 4) {
        offsetMinutes += int.parse(cleaned.substring(2, 4));
      }
    }
    final offsetMs = sign * offsetMinutes * 60 * 1000;
    final utcMs = DateTime.utc(year, month, day, hour, minute, second,
            micro ~/ 1000, micro % 1000)
        .millisecondsSinceEpoch -
        offsetMs;
    return DateTime.fromMillisecondsSinceEpoch(utcMs, isUtc: true);
  }
}

/// Parse a duration string. Returns null if not parseable.
Duration? parseDuration(String value) {
  // Standard: [-]D days, HH:MM:SS[.ffffff]
  final standard = RegExp(
    r'^(?:(-?\d+) days?, )?'
    r'(?:(?:(-?\d+):)(?=\d+:\d+))?'
    r'(?:(-?\d+):)?'
    r'(-?\d+)'
    r'(?:\.(\d{1,6})\d{0,6})?$',
  );
  final m = standard.firstMatch(value);
  if (m != null) {
    final days = m.group(1) != null ? int.parse(m.group(1)!) : 0;
    final hours = m.group(2) != null ? int.parse(m.group(2)!) : 0;
    final minutes = m.group(3) != null ? int.parse(m.group(3)!) : 0;
    final seconds = int.parse(m.group(4)!);
    var micros = 0;
    if (m.group(5) != null) {
      micros = int.parse(m.group(5)!.padRight(6, '0'));
    }
    return Duration(
        days: days,
        hours: hours,
        minutes: minutes,
        seconds: seconds,
        microseconds: micros);
  }
  // ISO 8601: P[nD]T[nH][nM][nS]
  final iso = RegExp(
    r'^([-+]?)P'
    r'(?:(\d+(?:\.\d+)?)D)?'
    r'(?:T'
    r'(?:(\d+(?:\.\d+)?)H)?'
    r'(?:(\d+(?:\.\d+)?)M)?'
    r'(?:(\d+(?:\.\d+)?)S)?'
    r')?$',
  );
  final m2 = iso.firstMatch(value);
  if (m2 != null) {
    final sign = m2.group(1) == '-' ? -1 : 1;
    final days = m2.group(2) != null ? double.parse(m2.group(2)!) : 0.0;
    final hours = m2.group(3) != null ? double.parse(m2.group(3)!) : 0.0;
    final minutes = m2.group(4) != null ? double.parse(m2.group(4)!) : 0.0;
    final seconds = m2.group(5) != null ? double.parse(m2.group(5)!) : 0.0;
    final totalUs = ((days * 86400 + hours * 3600 + minutes * 60 + seconds) *
            1000000)
        .round();
    return Duration(microseconds: sign * totalUs);
  }
  return null;
}
