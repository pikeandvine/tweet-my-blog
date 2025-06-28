# Feature Spec: Human-like Scheduling for tweet-my-blog

## Objective

Update the `tweet-my-blog` GitHub Actions workflow to:

- Run once daily, but at **human-like times** (e.g. 9:12am, 10:23am, etc.)
- Schedule Actions to run at **"odd" minute offsets** within the hour (e.g., 12, 23, 08)
- Constrain scheduled times between **6am and 4pm PDT**
- Add a **random delay of 0–180 seconds** after match is found, to reduce robotic timing
- Include a toggle (`ENABLE_DELAY`) to turn off the delay for GitHub Actions cost-conscious users

---

## Key Features

### 1. GitHub Actions Scheduled at "Odd" Times

Use multiple `cron` entries to trigger the workflow at minute offsets past the hour, such as:

```yaml
on:
  schedule:
    - cron: "12 13 * * *"  # 6:12am PDT (13 UTC)
    - cron: "23 14 * * *"  # 7:23am PDT (14 UTC)
    - cron: "08 15 * * *"  # 8:08am PDT (15 UTC)
    - cron: "37 16 * * *"  # 9:37am PDT (16 UTC)
    - cron: "19 17 * * *"  # 10:19am PDT (17 UTC)
    - cron: "26 18 * * *"  # 11:26am PDT (18 UTC)
    - cron: "43 19 * * *"  # 12:43pm PDT (19 UTC)
    - cron: "17 20 * * *"  # 1:17pm PDT (20 UTC)
    - cron: "33 21 * * *"  # 2:33pm PDT (21 UTC)
    - cron: "11 22 * * *"  # 3:11pm PDT (22 UTC)
    - cron: "29 23 * * *"  # 4:29pm PDT (23 UTC)
  workflow_dispatch:
```

> These times reflect random-seeming offsets between 6am and 4:59pm PDT (13–23 UTC).

### 2. Random Delay (Optional)

If the delay switch is **enabled** via the `ENABLE_DELAY` environment variable:

- Wait a random number of seconds between `0` and `180` before executing `main.py`
- This introduces human-like inconsistency without excessive GitHub runner usage

### 3. Delay Toggle

Set in the GitHub Actions workflow YAML:

```yaml
env:
  ENABLE_DELAY: "true"
```

If set to `"false"` (or missing), the delay step is skipped.

---

## Files

### `.github/workflows/tweet.yaml`

- Multiple scheduled times as shown above
- Steps:
  - Checkout
  - Python setup
  - Optional delay step
  - Tweet posting step

### `tweet_bot/random_delay.py`

```python
import os
import random
import time

if os.getenv("ENABLE_DELAY", "false").lower() == "true":
    delay = random.randint(0, 180)
    print(f"Delaying execution by {delay} seconds for human-like variability...")
    time.sleep(delay)
else:
    print("Delay disabled, proceeding immediately.")
```

---

## Benefits

- Tweets appear more natural and less bot-like
- GitHub Actions usage stays low (1 scheduled run/day, minimal active time)
- Easy to turn off delay if cost or speed is a concern

---

## Stretch Goals (Future)

- Randomize daily scheduled time from a pool
- Use GitHub API to update the cron dynamically (rare but possible)
- Integrate weekday vs weekend behavior