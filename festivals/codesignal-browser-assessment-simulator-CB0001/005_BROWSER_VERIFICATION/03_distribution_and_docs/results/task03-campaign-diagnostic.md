# Clean campaign clone diagnostic — 2026-09-10

This is a local rehearsal, not final remote release reproduction or task completion.

- Cloned the campaign with `git clone --no-hardlinks --no-recurse-submodules`
  into the owned temporary release root, outside the festival and source checkout.
- Clone HEAD: `2b3090746398987b38e02723be03bcab81d080ac`; initial status clean.
  The committed wheel evidence is present in the clone.
- Actual campaign HEAD gitlink remains
  `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`. Release integration has not happened.
- In the temporary clone only, configured the simulator's local repository URL,
  staged the exact reviewed gitlink `b61d136f2fd938ef7236c1d4331ae32fb561fd2b`,
  and ran targeted `git -c protocol.file.allow=always submodule update --init --
  projects/codesignal-practice-simulator`. No other submodule was initialized.
- The initialized submodule HEAD equals the reviewed checkpoint exactly and its
  status is clean. The only temporary campaign index change is that one gitlink.
- In the cloned submodule, tracked and git-boundary manifest verification passed;
  `python3 scripts/check_assets.py` passed all 13 assets. Manifest SHA256:
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- No real cache or attempts were fetched/copied. Existing campaign changes in
  Resume, job-search-automation, the resume site, and application feedback were
  preserved. The real campaign index remains empty and its gitlink unchanged.

The project-clone canonical-command result is recorded separately. The final
remote project/campaign clone verification, real pointer integration, and full
task acceptance remain pending; this temporary staged-pointer rehearsal cannot
substitute for them. The owned temporary campaign clone was moved to macOS Trash
after verification; its original path was checked absent. This also removed its
temporary staged pointer and initialized submodule without modifying the real
campaign or project. Recovery remains possible from Trash.
