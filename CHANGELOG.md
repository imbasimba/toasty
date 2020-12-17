# toasty 0.6.2 (2020-12-17)

- Add a few knobs so that we can get the Djangoplicity pipeline working for
  `eso.org`
- Tidy up the pipeline output a little bit.


# toasty 0.6.1 (2020-12-09)

Some fixes to the pipeline functionality:

- Add globbing support for the operations that take image-id arguments
- Attempt to fix crashing on non-actionable candidates on Windows
- Improvements to the relevant docs
- Bump the required version of `wwt_data_formats` to the correct value


# toasty 0.6.0 (2020-12-04)

- Start supporting the pipeline processing framework! See the documentation for
  a workflow outline and explanations of the `toasty pipeline` commands (#40,
  @pkgw)
- Start supporting FITS tiling! FITS files can now be procesed with the
  `tile-study` subcommand (@astrofrog, #30)
- In service of the above, improve how image modes and their corresponding file
  formats are handled. The internal systems are now more sensible and can
  properly handle FITS images (@astrofrog, #30)
- Also start supporting the attachment of WCS information to images. This should
  help us make it so less special-casing of different image types is needed.
- Fix some dumb bugs in the merging machinery so that our high-level tiles
  don't come out busted.


# toasty 0.5.0 (2020-10-26)

- Add a `plate-carree-ecliptic` projection mode, for images that are in a plate
  carrée projection but in a barycentric true ecliptic coordinate system
- Add a `--crop` option to generic image-loading commands that allows you to crop
  pixels off the edges of input images before processing them.
- Add a new image mode, “F16x3”, corresponding to three planes of “half
  precision” floating-point numbers. This is useful for high-dynamic-range (HDR)
  processing.
- Process OpenEXR files using the new F16x3 mode, rather than converting them to
  RGB upon load.
- Add a `--type` option to the `cascade` command to allow cascading more file
  types than just PNG: now arrays of floating-point data can be cascaded from
  the command line, too, including F16x3 tiles.
- Add a `transform fx3-to-rgb` command to transform three-plane floating-point
  pyramids into RGB data. In combination with the above features, this means
  that you can tile large OpenEXR files and preserve the dynamic range all the
  way down to the base tile. If the image is converted to RGB first, the
  dynamic-range limitations of 8-bit colors cause the detail to be washed out as
  the image is downsampled.

Some lower-level changes:

- Group pipeline commands under a subcommand
- Rename `healpix-sample-data-tiles` to `tile-healpix`
- Start building support for multi-generic-WCS tiling
- Avoid deadlocking in very large cascade operations
- Avoid annoying warnings in the averaging_merger when there are NaNs
- Specify UTF-8 encoding whenever working with text

# toasty 0.4.0 (2020-10-05)

- In WTML outputs, omit the <Place> wrapper for all-sky data sets
- When using `tile-allsky` in `plate-carree-planet` mode, use the "Planet" data
  set type
- Add `--name` options to `tile-allsky` and `tile-study`

# toasty 0.3.3 (2020-09-29)

- Make sure to close WWTL files after reading them in. May fix the test suite
  on some Windows machines.

# toasty 0.3.2 (2020-09-29)

- Switch to Cranko for versioning and release management, and Azure Pipelines
  for CI/CD, and Codecov.io for coverage monitoring.
- Fix tests on Windows, where there is no `healpy`

# 0.3.1 (2020 Sep 21)

- If PIL is missing colorspace support, don't crash with an error, but provide a
  big warning.
- Add a `plate-carree-galactic` projection type, for equirectangular images in
  Galactic coordinates.
- In the plate carrée image samplers, round nearest-neighbor pixel coordinates
  rather than truncating the fractional component. This should fix a half-pixel
  offset in TOASTed maps.
- Remove some old functionalities that are currently going unused, and not
  expected to become needed in the future.

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
