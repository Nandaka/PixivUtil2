/// PixivUtilGUI - placeholder.
///
/// The original Python GUI uses tkinter, which has no direct Dart equivalent.
/// To build a GUI in Dart, use Flutter (`flutter create`) and depend on this
/// library's models, browser, and handlers. This file documents the entry
/// point and the expected layout.
library;

import 'common/pixiv_browser.dart';
import 'common/pixiv_config.dart';
import 'pixiv_db_manager.dart';

/// Stub class describing the expected GUI surface.
///
/// A future Flutter app would instantiate [PixivConfig], [PixivBrowser], and
/// [PixivDBManager] and wire them up to widgets that present the same menu
/// options as the CLI in `bin/pixiv_util2.dart`.
class PixivUtilGUI {
  final PixivConfig config;
  final PixivBrowser browser;
  final PixivDBManager dbManager;

  PixivUtilGUI({
    required this.config,
    required this.browser,
    required this.dbManager,
  });

  Future<void> run() async {
    throw UnimplementedError(
      'Build a Flutter app that imports this library and wires up the '
      'PixivBrowser, PixivConfig, and PixivDBManager. See the CLI in '
      'bin/pixiv_util2.dart for the available operations.',
    );
  }
}
