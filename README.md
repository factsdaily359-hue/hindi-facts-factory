# Hindi Facts Factory

Daily Hindi facts video generator. The scheduled cloud workflow currently creates one Short and one long-form review video. Upload is intentionally disabled by default.

## Current workflow

- Scheduled cloud render: daily at 10:00 IST using GitHub-hosted Ubuntu.
- Output: Short, long video, metadata JSON, and review thumbnails.
- YouTube upload: disabled (NO_UPLOAD=true in the workflows; the Python default is also safe).
- AI content generation: Gemini API. Free-tier quota limits still apply.
- Cloud rendering: Blender runs on a GitHub-hosted CPU runner; no cloud GPU is guaranteed.

## Optional local RTX 2060 render worker

The repository includes a manual workflow named **Local RTX 2060 Review Render**. It uses a Windows self-hosted GitHub Actions runner and never uploads to YouTube.

### One-time Windows setup

1. Install the latest NVIDIA driver for the RTX 2060.
2. Install Blender 4.2 or newer. During installation, note its folder (commonly `C:\Program Files\Blender Foundation\Blender 4.x\`).
3. Install FFmpeg and add its `bin` folder to the Windows PATH.
4. Make sure Python 3.11 is installed.
5. Open this repository on GitHub, then go to **Settings → Actions → Runners → New self-hosted runner**.
6. Select **Windows → x64** and follow GitHub's page to download and extract the runner into a folder such as `C:\actions-runner`.
7. In PowerShell opened in that folder, run the exact `config.cmd` command shown by GitHub. Add the custom label `gpu` when prompted (or use `--labels gpu`).
8. Start the runner with `run.cmd`. Keep the PC awake and connected to the internet while a local render is running. For persistent operation, configure the runner as a Windows service using GitHub's instructions.
9. Confirm that the runner appears **Online** in the repository's Runners page.

### Run a local review render

1. Open the repository's **Actions** tab.
2. Select **Local RTX 2060 Review Render**.
3. Click **Run workflow**.
4. When the run completes, download the `local-rtx2060-review` artifact.

The runner must have the labels `self-hosted`, `Windows`, `X64`, and `gpu`. Do not paste the temporary runner registration token into chat or commit it to the repository.

## Important limitations

- The local RTX workflow is currently a manual review-render workflow. The daily scheduled workflow still uses GitHub-hosted cloud CPU rendering. Automatic PC-online/local versus PC-off/cloud routing is not enabled yet.
- The present Blender scenes are procedural 3D objects and motion, not yet reference-level photorealistic CGI or a complete rigid-body physics simulator.
- The long-form renderer is still a 2D scene-card renderer pending its 3D upgrade.
- A generated thumbnail is a frame-based review thumbnail, not an AI-designed custom YouTube thumbnail.
- Gemini free-tier quota, GitHub Actions minutes, render time, and third-party service limits can prevent a daily run.
- No workflow should upload videos until the owner explicitly enables and approves that step.