# Helium AI Agent Guidelines

## 运作模型（先读这段）

这是 Helium Windows 版的个人自用打包仓（上游 `imputnet/helium-windows` 的 fork）。规则与 `helium` 那边一致：只做 Windows 版，产物只通过 GitHub Releases 分发，不向上游提 PR，不发其他地方。沟通、文档、提交说明用中文。

编译、打包、签名、发布一律在 GitHub Actions；本地不搭 Chromium 构建环境，也不为了"验证能编译"去准备 VS + depot_tools。

| 改动 | 本地做 | 停手条件 |
| --- | --- | --- |
| `build.py`、`package.py`、`signing.py` | `py_compile`，必要时读一下改动路径 | 需要 Chromium 树或 VS 工具链才能验证时直接跳过，明确说"未本地验证" |
| `.github/workflows/*.yml` | 结构检查（job/needs/inputs 对得上） | 能否跑通只能由 Actions 判定 |
| `patches/`、`installer/` | 文件存在、series 与文件双向一致 | 同上 |

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `helium-chromium/` | submodule，指向上游 `imputnet/helium`（本仓库所有 patch 的上游） |
| `patches/` | 本平台自己的 patch，`series` 顺序应用在 helium-chromium 的 patch 之上 |
| `build.py` | 拉源码、解压依赖、应用 patch、跑 GN/ninja 出 `build/` |
| `package.py` | 打包原语：`stage_build`、`build_packages`、`verify_packages` |
| `signing.py` | 打包编排入口（`python signing.py --arch ...`）；签名已移除，文件名沿用旧名 |
| `installer/` | NSIS 安装脚本（`helium.nsi`） |
| `flags.windows.gn` | Windows 专用 GN 参数（PGO phase 2、x64、component build 关） |
| `downloads.ini`、`downloads.x64.ini` | 平台侧额外下载物 |
| `revision.txt` | 平台版本第四段，`0.20.3.1` 里的 `1` |
| `devutils/` | `update_patches.sh`、`check_patch_files.sh`、`set_quilt_vars.sh`、`print_tag_version.sh` |

## 构建与 Release 怎么走

`main.yml` 是唯一入口，只有 `workflow_dispatch`（不会因 push 自动触发），两个输入：`runner`（默认 `windows-2025`）和 `do-release`（默认 `false`）。**只构建 x86_64**：`arm64` 的矩阵项已删，stage/package 里的 `arm` 一律传 `false`（`stage/index.js` 里的 arm 分支还在，但不可达）。

- `build` job 调 `build-steps.yml`；后者串起 15 段 `build-stage.yml`，每段把产物传成 artifact，下一段接着跑——单个 runner 撑不住整场编译，所以构建天然可能在中途停住，断点续跑靠 `from-artifact`。
- 每段结束由 `package` job 打包，**不签名**：`signing.py` 只做 `stage_build` → `build_packages` → `verify_packages`，再由 stage action 上传。`pywin32` 要留着——`package.py:161` 的 `rebuild_mini_installer` 用 `win32api` 改 mini_installer 的资源，跟签名无关。
- `do-release=true` 才跑 `publish-release`：版本号取自 `helium-chromium/utils/helium_version.py --print --tree helium-chromium --platform-tree .`（即四段版本，如 `0.20.3.1`），只下载 `helium-x86_64` 一个 artifact，挂到本仓库的 Releases。这个 job 跑在 `ubuntu-latest` 上——它只发 Release，不做编译，换成 Windows runner 只会更慢。
- `lint.yml`（patch series 校验）和 `bump.yml`（抬子模块 + 开 PR，需要 `GHPAT`）都已删除：前者跟构建重复，后者是上游维护流程，自用 fork 用不上。要恢复从 git 历史取。

对自用 fork 有几个现实约束，改之前先想清楚，不要照抄上游：

1. **签名已移除**（2026-10-30）：Azure Trusted Signing 的 6 个 secret、`signing.py` 里的 dlib/`signtool` 路径、`setup-dotnet` + `nuget install` 都已删，`package` 现在只打包不签名。产物无签名，下载后 SmartScreen 会拦一次，这是接受了的行为。将来若接自动更新：不签名就只能用 WinSparkle 的 EdDSA key 校验，走 Authenticode 则需要签过名且被系统信任链认可的证书。
2. WinSparkle 自动更新仍是关的：`chrome/updater/winsparkle.gni` 里 `enable_winsparkle = false`，`build.py:339` 只在 `WINSPARKLE_ED_KEY` 与 `WINSPARKLE_AUTHENTICODE_ORG` 同时存在时才置 true；两处 vars 引用已从 workflow 删掉，`build.py` 用 `''` 兜底。将来真启用时 `winsparkle_authenticode_org` 必须等于签名证书 Subject 的 `O=`。

## 开发后验证 Actions

```bash
gh run list --repo <owner>/helium-windows --limit 10
gh run watch <run-id> --repo <owner>/helium-windows          # 15 段构建，慢是常态
gh run view <run-id> --repo <owner>/helium-windows --log-failed
gh run rerun <run-id> --failed                               # 断在某一段时重跑失败段
gh release view <tag> --repo <owner>/helium-windows          # tag 形如 0.20.3.1
```

只关心这一个 build 能否出包、Release 是否挂上。
