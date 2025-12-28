# PixivUtil2 v20251112 - 自定义修改说明

## 概述

本文档描述对 PixivUtil2 v20251112 所做的修改，目标是增强预热（preheat）功能、支持按下载数排序成员、以及添加标记已完成作者的功能。

## 核心功能新增

### 1. 预热断点续传支持

**修改文件：** `handler/PixivBookmarkHandler.py`, `common/PixivHelper.py`

- **断点续传：** 预热进度现保存至 `<list_file>.preheat_progress.json`，允许中断后继续处理成员主页。
- **进度追踪：** 记录已处理的成员 ID 及元数据（时间戳、列表文件、总数）。
- **恢复逻辑：** 预热以 `resume=True` 运行时，跳过已处理的成员。
- **配置控制：** 
  - `preheatDelaySeconds` 或 `preheatDelay`（config.ini）控制请求间延迟（最小 0.1 秒）。
  - 可通过命令行或菜单输入覆盖。

**实现细节：**
- 辅助函数：`_load_preheat_progress()`、`_save_preheat_progress()`
- 优雅处理中断（Ctrl+C），退出前刷新进度
- 定期刷新进度（默认每 10 个成员）以最小化数据丢失

### 2. 可配置成员下载顺序

**修改文件：** `common/PixivConfig.py`, `handler/PixivBookmarkHandler.py`

- **新增配置项：**
  - `memberOrder`（Settings 段）：控制关注作者的排序方式
  - 支持值：`"fewest_first"`（升序）、`"most_first"`（降序）、或空字符串（不排序）

- **排序逻辑：** 处理书签/关注作者时：
  - 从 DB 检索各成员的 `total_images`（由预热填充）
  - 若无此值，回退至本地图片计数
  - 少作品的成员优先处理（fewest_first 模式）

**实现细节：**
- 新函数：PixivBookmarkHandler 中的 `_sort_followed_members()`
- 去重成员列表（保留首次出现的顺序）
- 兼容本地 DB 和回退图片计数

### 3. 数据库中的总作品数追踪

**修改文件：** `PixivDBManager.py`

- **数据库模式：** 向 `pixiv_master_member` 表添加 `total_images` 列
- **迁移：** 若列不存在，`createDatabase()` 自动添加
- **新增方法：**
  - `updateMemberTotalImages(memberId, totalImages)` - 更新或插入成员总数
  - `selectMemberTotalImagesMap(member_ids=None)` - 返回 `{member_id(int): total_images(int)}` 映射

- **预热整合：** 预热期间，获取成员主页并存储 `artist.totalImages` 至 DB 以供未来排序使用

### 4. 修复下载路径生成

**修改文件：** `handler/PixivBookmarkHandler.py`, `common/PixivHelper.py`

- **问题：** 之前的行为强制下载至旧的每作者保存路径，无视配置
- **解决：** 修改 `process_bookmark()` 向 `process_member()` 传递 `user_dir=''`，允许尊重 `config.filenameFormat` 和 `config.rootDirectory`
- **结果：** 所有下载现遵循配置的文件名格式和根目录

### 5. 浮点延迟支持

**修改文件：** `common/PixivHelper.py`

- **函数：** `print_delay(retry_wait)` 现接受浮点值（如 0.1、0.5）
- **行为：** 精确睡眠指定时长，无每秒循环开销
- **输出：** 单一简洁状态消息，而非重复每秒消息

### 6. 健壮的 JSON 进度文件处理

**修改文件：** `model/PixivImage.py`

- **问题：** `WriteJSON()` 在移除不存在的字段时可能抛出 KeyError
- **解决：** 使用 `dict.pop(key, None)` 安全移除字段
- **结果：** JSON 结构变化或字段缺失时不会崩溃

### 7. 扫描并标记已完成成员

**修改文件：** `PixivUtil2.py`, `handler/PixivBookmarkHandler.py`

- **新菜单选项：** `5b. 扫描本地关注作者并标记已完成`
- **函数：** PixivBookmarkHandler 中的 `scan_and_mark_completed_members()`

- **默认行为（已调整为“增量补全”模式）：**
  - `compare_remote=True`：默认会联网拉取作者远端作品 ID 列表（精确集合），用于三方对比（远端 vs DB vs 本地文件）。
  - `download_missing=True`：默认会“只下载缺失作品”（增量更新）。
  - `dry_run=True`：默认仅预览，不写入 progress 文件；确认无误后再设为 `n` 落盘。
  - `download_limit=None`：默认不限制单作者下载数量（可在提示中输入整数作为安全阈值）。

- **一致性目标（避免反复扫盘）：**
  - 下载缺失图片成功后，DB 会被更新（由现有下载逻辑写入）。
  - 下一次判断优先使用 DB 中的 save_name + 文件存在性来确认“已拥有”，减少每次都完整扫盘的必要性。

- **行为：**
  - 扫描关注成员：
    - DB 已下载集合：从 `pixiv_master_image` 中读取 save_name != N/A 且本地文件存在的 image_id。
    - 本地文件集合：从已知作者目录中解析文件名提取 image_id（启发式，作为补充）。
    - 远端集合（可选但默认开启）：翻页获取作者作品 image_id 列表。
  - 计算缺失：`missing = remote_set - (db_set ∪ local_set)`
  - 若 `download_missing=True`：逐个下载 missing 图片（只补缺，不删除本地多余文件）。
  - 仅当“远端集合已被本地/DB 覆盖”时才会将作者加入 progress 文件的 `done` 列表。

- **整合：**
  - 新菜单处理器：PixivUtil2.py 中的 `menu_scan_and_mark_complete()`
  - 使用与预热相同的进度文件格式以保持兼容
  - 尊重 `config.rootDirectory` 和 `config.filenameFormat`

## 配置变更

### 新增 Config.ini 项（Settings 段）

```ini
[Settings]
preheatDelaySeconds = 0.1          # 预热延迟秒数（支持浮点）
preheatDelay = 0.1                 # preheatDelaySeconds 的替代名称
memberOrder = fewest_first         # 排序关注成员：fewest_first、most_first 或空
rootDirectory = G:\Porn\Pixiv      # 下载根目录

[Filename]
filenameFormat = %member_id% %artist%\\%image_id% - %title%\\%image_id% - %title%
```

## 使用示例

### 1. 预热并支持续传

```bash
python PixivUtil2.py
# 选择选项：5a
# 输入列表文件或按 Enter 使用默认值
# 预热获取成员主页并保存进度
# 按 Ctrl+C 中断 - 进度已保存
# 再次运行即从中断处继续
```

### 2. 按少作品优先下载

```bash
# 确保预热已填充 DB 的 total_images
# 在 config.ini 中设置 memberOrder = fewest_first
# 选择选项：5（从关注的作者下载）
# 作品较少的成员会优先下载
```

### 3. 扫描并标记已完成作者

```bash
python PixivUtil2.py
# 选择选项：5b
# Compare remote? 默认 Y（精确三方对比）
# Download missing? 默认 Y（增量补全缺失）
# Dry run? 默认 Y（先预览，不写入进度文件）
# Download limit per member: 默认空（不限制）
# 确认输出无误后，再次运行并设置 dry_run=n 以写入进度
```

## 修改文件清单

| 文件 | 变更 |
|------|------|
| `PixivUtil2.py` | 新增菜单选项 `5b` 和 `menu_scan_and_mark_complete()` 处理器 |
| `handler/PixivBookmarkHandler.py` | 新增预热断点续传辅助函数、排序逻辑和 `scan_and_mark_completed_members()` |
| `common/PixivConfig.py` | 注册 `preheatDelaySeconds`、`preheatDelay`、`memberOrder` 配置项 |
| `common/PixivHelper.py` | 更新 `print_delay()` 以接受浮点值并简化延迟显示 |
| `PixivDBManager.py` | 新增 `total_images` 列迁移和 DB 管理方法 |
| `model/PixivImage.py` | 修复 `WriteJSON()` 使用 `pop(key, None)` 安全移除键 |

## 向后兼容性

- **数据库：** 通过 `createDatabase()` 自动迁移模式；现有 DB 首次运行时更新
- **配置：** 所有新配置项有合理的默认值；现有 config.ini 文件兼容
- **API：** 公有方法签名无破坏性变化
- **菜单：** 新选项为补充；现有选项保持不变

## 技术细节

### 预热进度文件格式

```json
{
  "done": ["123456", "789012", "345678"],
  "updated_at": "2025-12-26 10:30:45",
  "list_file": "followed_artists.txt",
  "total": 1005
}
```

### 数据库模式变更

```sql
ALTER TABLE pixiv_master_member ADD COLUMN total_images INTEGER;
```

### 成员排序算法

1. 从 DB 获取各成员的 `total_images`
2. 若无此值，回退至本地图片计数
3. 按 total_images 排序（fewest_first 模式升序）
4. 保持稳定排序（并列项保留原顺序）

## 已知限制

- **本地文件解析（启发式）：** 本地文件名提取 image_id 使用正则匹配数字串，能覆盖常见命名，但对高度自定义命名可能不完全准确；精确性以 `compare_remote=True` 的远端 ID 列表为准。
- **联网成本：** `compare_remote=True` 会为每位作者拉取多页数据，耗时较长；请合理配置延迟（`preheatDelaySeconds`）避免限流。
- **下载缺失：** 仅补缺，不会删除本地“多余”文件；如本地存在额外文件不影响完成判定（以远端集合是否被覆盖为判断依据）。

## 故障排除

### 预热不继续续传

- 检查 `<list_file>.preheat_progress.json` 存在且可读
- 删除或重命名进度文件以强制完整预热：`del followed_artists.txt.preheat_progress.json`

### 排序未应用

- 确保 DB 已填充 `total_images`（先运行预热）
- 检查 config.ini 中 `memberOrder` 设置为 `fewest_first` 或 `most_first`
- 验证配置重载：菜单中按 `r` 重载 config.ini

### 已完成成员未标记

- 确保 DB 和本地下载同步
- 首先使用 `dry_run=True`（默认）预览
- 若 DB 某些成员缺少 total_images，检查 `compare_remote=True`

## 未来增强

未来版本的潜在改进：
- 批量标记多个成员为已完成
- 自动重新下载已完成文件夹中的缺失图片
- 扫描操作的进度条
- 导出完成状态至外部格式
- 按成员完成统计
