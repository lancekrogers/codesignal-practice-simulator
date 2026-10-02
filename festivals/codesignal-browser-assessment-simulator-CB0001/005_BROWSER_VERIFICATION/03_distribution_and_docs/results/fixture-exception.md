# Approved clean-clone fixture exception — 2026-09-10

The operator approved moving forward after the coordinator explained the exact
exception: use the existing fetch command to download the seven approved pinned
assessment files into ignored caches inside owned temporary verification clones,
validate their hashes, run canonical verification, and remove the clones afterward.
No cache bytes will be committed, published, copied from existing campaign caches,
or inspected as candidate/assessment source. No real attempts are in scope.

This overrides task 03's synthetic-only setup restriction solely for its canonical
fixture-cache verification prerequisite and final clean-clone release reproduction.
Browser lifecycle/scoring tests continue to use synthetic fixtures. Provenance
checks remain strict, and the wheel remains free of FETCH_ONLY bytes.

User authorization: “Okay, can you help me with this please? Can you keep moving
it forward?” in response to the detailed exception and remaining-release-work
explanation. This resolves the recorded task 03 blocker; it does not waive any
test, review, local judge, or release gate.
