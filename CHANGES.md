# 0.3.0 (2020 Sep 18)

- Attempt to properly categorize Cython as a build-time-only dependency. We don't
  need it at runtime.

# 0.2.0 (2020 Sep 17)

- Add a first cut at support for OpenEXR images. This may evolve since it might
  be valuable to take more advantage of OpenEXR's support for high-dynamic-range
  imagery.
- Add cool progress reporting for tiling and cascading!
- Fix installation on Windows (hopefully).
- Add a new `make-thumbnail` utility command.
- Add `--placeholder-thumbnail` to some tiling commands to avoid the thumbnailing
  step, which can be very slow and memory-intensive for huge input images.
- Internal cleanups.

# 0.1.0 (2020 Sep 15)

- Massive rebuild of just about everything about the package.
- New CLI tool, `toasty`.

# 0.0.3 (2019 Aug 3)

- Attempt to fix ReadTheDocs build.
- Better metadata for PyPI.
- Exercise workflow documented in `RELEASE_PROCESS.md`.

# 0.0.2 (2019 Aug 3)

- Revamp packaging infrastructure
- Stub out some docs
- Include changes contributed by Clara Brasseur / STScI
