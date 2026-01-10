# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0](https://github.com/aa-parky/pipeworks_name_generation/compare/v0.3.0...v0.4.0) (2026-01-10)


### Features

* **build_tools:** Add corpus_db tracking to interactive mode ([d1fa97f](https://github.com/aa-parky/pipeworks_name_generation/commit/d1fa97fe3901b6035912e179528d8fb1b2d27073))
* **build_tools:** Add corpus_db_viewer TUI for database inspection ([7df65c3](https://github.com/aa-parky/pipeworks_name_generation/commit/7df65c38f73847befbce50dadd7c635002f85206))
* **build_tools:** Add extractor identifiers to output directory names ([5bbe49b](https://github.com/aa-parky/pipeworks_name_generation/commit/5bbe49bee40ab251715bd4cc6ad9e00fac3dc554))
* **build_tools:** Add NLTK syllable extractor for phonetic syllabification ([16c5237](https://github.com/aa-parky/pipeworks_name_generation/commit/16c5237a8d38e6c7ab3277716188d8595cced9a8))
* **build_tools:** Add NLTK syllable normaliser with fragment cleaning ([baf223a](https://github.com/aa-parky/pipeworks_name_generation/commit/baf223a0e7d08efe7678c4c6b821abfa03679942))
* **build_tools:** Add pyphen_ prefix to syllable normaliser outputs ([c1c2b8a](https://github.com/aa-parky/pipeworks_name_generation/commit/c1c2b8abea384a94b8c1bf49bedef8cfe10b5df1))
* **build_tools:** Make pyphen extractor language argument optional ([deeb4c7](https://github.com/aa-parky/pipeworks_name_generation/commit/deeb4c739c0bf7d841dff7e89d436bb2375a10e7))


### Documentation

* **build_tools:** Add Basic Usage sections to CLI documentation ([a482971](https://github.com/aa-parky/pipeworks_name_generation/commit/a48297100c1bdde2f895067e7cfa46357b163297))
* **build_tools:** Add documentation for NLTK syllable extractor ([8121d04](https://github.com/aa-parky/pipeworks_name_generation/commit/8121d04a32eccfce57166564280f203e892d942f))
* **build_tools:** Add NLTK normaliser documentation ([e06da84](https://github.com/aa-parky/pipeworks_name_generation/commit/e06da84039739242b6bc4b8649ec425fde065f07))
* **build_tools:** Add Sphinx documentation for corpus_db_viewer ([0681e4d](https://github.com/aa-parky/pipeworks_name_generation/commit/0681e4dd9075a87f5d58ae8e813e465568452f28))
* **build_tools:** Fix bash command formatting in CLI documentation ([4dfbd87](https://github.com/aa-parky/pipeworks_name_generation/commit/4dfbd87a16d1848ff13baf9dee24554785f254bb))
* **build_tools:** Fix bash formatting in module docstrings ([8162ef6](https://github.com/aa-parky/pipeworks_name_generation/commit/8162ef61186723b6af1d85504d4d3d5bfd84edb5))
* **build_tools:** Improve corpus_db_viewer documentation formatting ([b652ac1](https://github.com/aa-parky/pipeworks_name_generation/commit/b652ac1def8afe110e9f06c2541faed157ca51fa))
* **build_tools:** Standardize RST documentation and eliminate redundancy ([12bb279](https://github.com/aa-parky/pipeworks_name_generation/commit/12bb2790d262b5085ff6c2aabb34903ed696c577))
* **build_tools:** Update NLTK extractor docs for duplicate preservation ([3971524](https://github.com/aa-parky/pipeworks_name_generation/commit/39715240a2fa93994393750094eff124b153bde5))
* Fix broken cross-references in syllable_walk.rst ([f1c582a](https://github.com/aa-parky/pipeworks_name_generation/commit/f1c582ae07fc826a68653f5f4879c812a1659ff8))
* Update documentation titles and references for pyphen tools ([955c90b](https://github.com/aa-parky/pipeworks_name_generation/commit/955c90b14d371b0fb25dcaeef07132cd8078fd95))
* Update README and CLAUDE.md with NLTK extractor setup instructions ([8beb55c](https://github.com/aa-parky/pipeworks_name_generation/commit/8beb55c019560aaffdc445fb9a67ce502eb376f9))

## [0.3.0](https://github.com/aa-parky/pipeworks_name_generation/compare/v0.2.0...v0.3.0) (2026-01-08)


### Features

* Add batch processing CLI for syllable extractor ([1b6f1f8](https://github.com/aa-parky/pipeworks_name_generation/commit/1b6f1f85d8e576ee0891af506d278152a1cc2106))
* Add CLI support for automatic language detection ([60b1dd2](https://github.com/aa-parky/pipeworks_name_generation/commit/60b1dd20fe47b78e4bdbb4536412baba32bda0a4))
* Add comprehensive badges and codecov token to CI ([8cc155a](https://github.com/aa-parky/pipeworks_name_generation/commit/8cc155a77063f1cc5a2f1aaa7b4ce8586f5d7017))
* Add comprehensive CI/CD infrastructure and syllable extractor enhancements ([8487f9f](https://github.com/aa-parky/pipeworks_name_generation/commit/8487f9fedaeb522f755b91e7a0aad9546d0f4d1a))
* Add interactive HTML visualization to t-SNE visualizer ([8df6fa7](https://github.com/aa-parky/pipeworks_name_generation/commit/8df6fa739e97e362a1b02884fcc9eb23aa2e2b86))
* Add language code to output filenames for multi-language support ([ba1c3bf](https://github.com/aa-parky/pipeworks_name_generation/commit/ba1c3bfa34e633b9d28b33230c23e3b5c199d90a))
* Add optional language auto-detection for syllable extraction ([705261d](https://github.com/aa-parky/pipeworks_name_generation/commit/705261dfbd04cd39349c5d876a3318c2d0cad032))
* Add parameter logging and optional mapping to t-SNE visualizer ([f877d10](https://github.com/aa-parky/pipeworks_name_generation/commit/f877d106d660330b3b9bb9060639703888605b71))
* Add syllable walker for phonetic feature space exploration ([9d1b7e8](https://github.com/aa-parky/pipeworks_name_generation/commit/9d1b7e828dc322baf86e1e259e9541a9c230471f))
* Add t-SNE visualization tool for feature signature space ([5c8b44a](https://github.com/aa-parky/pipeworks_name_generation/commit/5c8b44a49b3e1603dcf48f7250a00d29e0af5bea))
* **build_tools:** Add corpus_db ledger for extraction run provenance ([53894ee](https://github.com/aa-parky/pipeworks_name_generation/commit/53894eefc4337d68f5c13e14152cf8e0cb6bc289))
* **build_tools:** Add syllable walker for phonetic space exploration ([058dec5](https://github.com/aa-parky/pipeworks_name_generation/commit/058dec5c6f5013b22ea56a083d1b965d8b6b8c76))
* **build_tools:** Integrate corpus_db into syllable_extractor CLI ([28c0ee9](https://github.com/aa-parky/pipeworks_name_generation/commit/28c0ee905cd6a0fef2f62aced92e2fe42f83d431))
* Complete Phase 1-4 of analysis refactoring - add dimensionality modules ([c8035e3](https://github.com/aa-parky/pipeworks_name_generation/commit/c8035e32648a7b843d452931bab64ad32c9cb276))
* Complete Phase 5-6 of analysis refactoring - add plotting modules and refactor tsne_visualizer ([d8d4097](https://github.com/aa-parky/pipeworks_name_generation/commit/d8d40976d09f20deedcd2c0205fe186aeea22585))
* Improve test coverage for syllable_extractor from 41% to 43% ([a149cb4](https://github.com/aa-parky/pipeworks_name_generation/commit/a149cb433c32e78de606169621fe056ea968342c))
* Make interactive t-SNE visualization responsive with min-width constraint ([9b8305a](https://github.com/aa-parky/pipeworks_name_generation/commit/9b8305a5c8d0bc684d4b57d1846339eef895014b))


### Bug Fixes

* Add missing sphinx-argparse dependency for ReadTheDocs ([a73bf2f](https://github.com/aa-parky/pipeworks_name_generation/commit/a73bf2f11983a548363e14a4255c87c2365f6aee))
* Clean up test_tsne_visualizer to keep only integration tests ([74b0cef](https://github.com/aa-parky/pipeworks_name_generation/commit/74b0cef315306309de54e33130f8ce98f4a24951))
* Configure matplotlib to use non-interactive backend for CI ([d7e0450](https://github.com/aa-parky/pipeworks_name_generation/commit/d7e04501aa249bfe81e90ad0fda9e43e9949729c))
* **corpus_db:** Store paths in POSIX format for cross-platform compatibility ([d4a19e5](https://github.com/aa-parky/pipeworks_name_generation/commit/d4a19e539eda03182479ccd1ae60976f5af28b25))
* **corpus_db:** Update test to use POSIX path format for comparison ([20c96f2](https://github.com/aa-parky/pipeworks_name_generation/commit/20c96f2b922fb4646f9d94c4aa59f896ddcc18a0))
* Create extractor instance after auto-detection for file saving ([3d5b13f](https://github.com/aa-parky/pipeworks_name_generation/commit/3d5b13f73bc0bb9c05d079a9588445553e9b4fce))
* **docs:** Link changelog.rst to auto-generated CHANGELOG.md ([dea252a](https://github.com/aa-parky/pipeworks_name_generation/commit/dea252a1e924f7ff7d05ceacb116881dfa4392f6))
* **docs:** Replace invalid JSON placeholder with valid example ([51e3b05](https://github.com/aa-parky/pipeworks_name_generation/commit/51e3b0529c5a754b563ea78d060e7137b76d151e))
* Expand mypy coverage to include tests and build_tools ([eb875c2](https://github.com/aa-parky/pipeworks_name_generation/commit/eb875c28829c74c252ff54a23e5259e409aefed4))
* Fix colorbar title overlapping with values in interactive t-SNE visualization ([4506aef](https://github.com/aa-parky/pipeworks_name_generation/commit/4506aefa2353e750dbd5fbb07e88a1ca53e6212c))
* Increase documentation warning threshold to accommodate dataclass warnings ([8d9657e](https://github.com/aa-parky/pipeworks_name_generation/commit/8d9657eb11a6ad1debe1916ce8e3f53e98f5998a))
* Make dimensionality modules optional and update CI dependencies ([c596a08](https://github.com/aa-parky/pipeworks_name_generation/commit/c596a08e502706d1719a3b21fba8fadc7100829c))
* Make pyphen import optional for documentation builds ([ecb33f1](https://github.com/aa-parky/pipeworks_name_generation/commit/ecb33f17cb155abeac5062d17246482339daf9b3))
* Make t-SNE visualizer dependencies optional for CI ([d14eac4](https://github.com/aa-parky/pipeworks_name_generation/commit/d14eac4e4d7d4c1855b5d3b65b6ce4bbac98624c))
* Remove _working/analysis_refactor.md from version control ([dc27bff](https://github.com/aa-parky/pipeworks_name_generation/commit/dc27bffd2ccc5c1b2da3e2d647142bb98fa833c5))
* Remove imported-members from autoapi to prevent duplicate warnings ([976cc36](https://github.com/aa-parky/pipeworks_name_generation/commit/976cc36253d092e917e7992123142b67c4a2b860))
* Resolve 3 CI test failures ([964c2d7](https://github.com/aa-parky/pipeworks_name_generation/commit/964c2d7d2f5f7da7eeea6ebf99b2337317cc4aae))
* Resolve Black formatting and mypy type errors in syllable extractor ([c3eb953](https://github.com/aa-parky/pipeworks_name_generation/commit/c3eb953ae2a7bf9bef961179802d13d65c5a91e1))
* Resolve markdownlint issues across documentation files ([56479a7](https://github.com/aa-parky/pipeworks_name_generation/commit/56479a7e81ac1ed306ce03069b40eb7811d6bbe3))
* Skip permission test on Windows (different permission model) ([6ddef3c](https://github.com/aa-parky/pipeworks_name_generation/commit/6ddef3c2845c65727f3f20cdc3d8b48a4338b737))
* Suppress expected Sphinx warnings for dataclass attributes and underscores ([495d5e3](https://github.com/aa-parky/pipeworks_name_generation/commit/495d5e3cd21fb444546bb265e5fac0d395ebd6c9))
* Use time.perf_counter() for higher precision timing on Windows ([8d32817](https://github.com/aa-parky/pipeworks_name_generation/commit/8d32817fcff22d9dd07cf4863b71aae0a90ec543))


### Documentation

* Add corpus_db to Claude Code documentation ([a261826](https://github.com/aa-parky/pipeworks_name_generation/commit/a2618269ecb7983e449b32ec99be5414d0ad45ba))
* Add corpus_db to README.md Build Tools section ([68912b1](https://github.com/aa-parky/pipeworks_name_generation/commit/68912b11701f48f7f39f6a4686afda9c608bffff))
* Add documentation content rules to CLAUDE.md ([23d9234](https://github.com/aa-parky/pipeworks_name_generation/commit/23d9234092e2fad821d77682deb9e78b6cf6a587))
* Add pre-commit hook for CLI documentation sync reminders ([4a064f3](https://github.com/aa-parky/pipeworks_name_generation/commit/4a064f3dec413ef3b01ad7b86033368dd1839087))
* Add table of contents and navigation links to README ([199e34b](https://github.com/aa-parky/pipeworks_name_generation/commit/199e34b27b6768ed9391affd4731f2e266894614))
* Automate CLI documentation with sphinx-argparse ([9a993e7](https://github.com/aa-parky/pipeworks_name_generation/commit/9a993e7bad5d5528089a5785ceb3aaf4e53db92a))
* **build_tools:** Add corpus_db to Sphinx documentation ([65faef7](https://github.com/aa-parky/pipeworks_name_generation/commit/65faef727b51dc55db0d466c7bc9f5d8d0c475d5))
* Complete Phase 7-8 of analysis refactoring with full documentation ([b70373d](https://github.com/aa-parky/pipeworks_name_generation/commit/b70373d7d23baa437ce8b50835927bb5f0ce5bfe))
* **pilot:** Refactor syllable_extractor to use auto-generated docs ([38fbfb2](https://github.com/aa-parky/pipeworks_name_generation/commit/38fbfb205f5b3f1f822778771b55ebdbc895eb3c))
* Refactor CLAUDE.md into modular documentation structure ([054ce99](https://github.com/aa-parky/pipeworks_name_generation/commit/054ce99b84ef061c16182384fcbaa1b3ae023389))
* Remove redundant API Reference section from analysis_tools.rst ([48fead8](https://github.com/aa-parky/pipeworks_name_generation/commit/48fead82c525bc74c933d67d98142416b4c8fc32))
* **rollout:** Complete auto-generated documentation refactor for all build tools ([97cdd8f](https://github.com/aa-parky/pipeworks_name_generation/commit/97cdd8f55feec3c392d3bf7bbae5edcfd5d1476c))
* Streamline README to focus on quick start and overview ([7bfad15](https://github.com/aa-parky/pipeworks_name_generation/commit/7bfad154cfd3c840b867a5a7083998ad311973a2))
* Update README with new syllable_extractor package usage ([3f06376](https://github.com/aa-parky/pipeworks_name_generation/commit/3f06376d2b4ffa4b2774227d5b7cdfd16659b13a))

## [0.2.1](https://github.com/aa-parky/pipeworks_name_generation/compare/v0.1.0...v0.2.1) (2026-01-08)


### Features

* Add batch processing CLI for syllable extractor ([1b6f1f8](https://github.com/aa-parky/pipeworks_name_generation/commit/1b6f1f85d8e576ee0891af506d278152a1cc2106))
* Add CLI support for automatic language detection ([60b1dd2](https://github.com/aa-parky/pipeworks_name_generation/commit/60b1dd20fe47b78e4bdbb4536412baba32bda0a4))
* Add comprehensive badges and codecov token to CI ([8cc155a](https://github.com/aa-parky/pipeworks_name_generation/commit/8cc155a77063f1cc5a2f1aaa7b4ce8586f5d7017))
* Add comprehensive CI/CD infrastructure and syllable extractor enhancements ([8487f9f](https://github.com/aa-parky/pipeworks_name_generation/commit/8487f9fedaeb522f755b91e7a0aad9546d0f4d1a))
* Add interactive HTML visualization to t-SNE visualizer ([8df6fa7](https://github.com/aa-parky/pipeworks_name_generation/commit/8df6fa739e97e362a1b02884fcc9eb23aa2e2b86))
* Add language code to output filenames for multi-language support ([ba1c3bf](https://github.com/aa-parky/pipeworks_name_generation/commit/ba1c3bfa34e633b9d28b33230c23e3b5c199d90a))
* Add optional language auto-detection for syllable extraction ([705261d](https://github.com/aa-parky/pipeworks_name_generation/commit/705261dfbd04cd39349c5d876a3318c2d0cad032))
* Add parameter logging and optional mapping to t-SNE visualizer ([f877d10](https://github.com/aa-parky/pipeworks_name_generation/commit/f877d106d660330b3b9bb9060639703888605b71))
* Add syllable walker for phonetic feature space exploration ([9d1b7e8](https://github.com/aa-parky/pipeworks_name_generation/commit/9d1b7e828dc322baf86e1e259e9541a9c230471f))
* Add t-SNE visualization tool for feature signature space ([5c8b44a](https://github.com/aa-parky/pipeworks_name_generation/commit/5c8b44a49b3e1603dcf48f7250a00d29e0af5bea))
* **build_tools:** Add corpus_db ledger for extraction run provenance ([53894ee](https://github.com/aa-parky/pipeworks_name_generation/commit/53894eefc4337d68f5c13e14152cf8e0cb6bc289))
* **build_tools:** Add syllable walker for phonetic space exploration ([058dec5](https://github.com/aa-parky/pipeworks_name_generation/commit/058dec5c6f5013b22ea56a083d1b965d8b6b8c76))
* **build_tools:** Integrate corpus_db into syllable_extractor CLI ([28c0ee9](https://github.com/aa-parky/pipeworks_name_generation/commit/28c0ee905cd6a0fef2f62aced92e2fe42f83d431))
* Complete Phase 1-4 of analysis refactoring - add dimensionality modules ([c8035e3](https://github.com/aa-parky/pipeworks_name_generation/commit/c8035e32648a7b843d452931bab64ad32c9cb276))
* Complete Phase 5-6 of analysis refactoring - add plotting modules and refactor tsne_visualizer ([d8d4097](https://github.com/aa-parky/pipeworks_name_generation/commit/d8d40976d09f20deedcd2c0205fe186aeea22585))
* Improve test coverage for syllable_extractor from 41% to 43% ([a149cb4](https://github.com/aa-parky/pipeworks_name_generation/commit/a149cb433c32e78de606169621fe056ea968342c))
* Make interactive t-SNE visualization responsive with min-width constraint ([9b8305a](https://github.com/aa-parky/pipeworks_name_generation/commit/9b8305a5c8d0bc684d4b57d1846339eef895014b))


### Bug Fixes

* Add missing sphinx-argparse dependency for ReadTheDocs ([a73bf2f](https://github.com/aa-parky/pipeworks_name_generation/commit/a73bf2f11983a548363e14a4255c87c2365f6aee))
* Clean up test_tsne_visualizer to keep only integration tests ([74b0cef](https://github.com/aa-parky/pipeworks_name_generation/commit/74b0cef315306309de54e33130f8ce98f4a24951))
* Configure matplotlib to use non-interactive backend for CI ([d7e0450](https://github.com/aa-parky/pipeworks_name_generation/commit/d7e04501aa249bfe81e90ad0fda9e43e9949729c))
* **corpus_db:** Store paths in POSIX format for cross-platform compatibility ([d4a19e5](https://github.com/aa-parky/pipeworks_name_generation/commit/d4a19e539eda03182479ccd1ae60976f5af28b25))
* **corpus_db:** Update test to use POSIX path format for comparison ([20c96f2](https://github.com/aa-parky/pipeworks_name_generation/commit/20c96f2b922fb4646f9d94c4aa59f896ddcc18a0))
* Create extractor instance after auto-detection for file saving ([3d5b13f](https://github.com/aa-parky/pipeworks_name_generation/commit/3d5b13f73bc0bb9c05d079a9588445553e9b4fce))
* **docs:** Link changelog.rst to auto-generated CHANGELOG.md ([dea252a](https://github.com/aa-parky/pipeworks_name_generation/commit/dea252a1e924f7ff7d05ceacb116881dfa4392f6))
* **docs:** Replace invalid JSON placeholder with valid example ([51e3b05](https://github.com/aa-parky/pipeworks_name_generation/commit/51e3b0529c5a754b563ea78d060e7137b76d151e))
* Expand mypy coverage to include tests and build_tools ([eb875c2](https://github.com/aa-parky/pipeworks_name_generation/commit/eb875c28829c74c252ff54a23e5259e409aefed4))
* Fix colorbar title overlapping with values in interactive t-SNE visualization ([4506aef](https://github.com/aa-parky/pipeworks_name_generation/commit/4506aefa2353e750dbd5fbb07e88a1ca53e6212c))
* Increase documentation warning threshold to accommodate dataclass warnings ([8d9657e](https://github.com/aa-parky/pipeworks_name_generation/commit/8d9657eb11a6ad1debe1916ce8e3f53e98f5998a))
* Make dimensionality modules optional and update CI dependencies ([c596a08](https://github.com/aa-parky/pipeworks_name_generation/commit/c596a08e502706d1719a3b21fba8fadc7100829c))
* Make pyphen import optional for documentation builds ([ecb33f1](https://github.com/aa-parky/pipeworks_name_generation/commit/ecb33f17cb155abeac5062d17246482339daf9b3))
* Make t-SNE visualizer dependencies optional for CI ([d14eac4](https://github.com/aa-parky/pipeworks_name_generation/commit/d14eac4e4d7d4c1855b5d3b65b6ce4bbac98624c))
* Remove _working/analysis_refactor.md from version control ([dc27bff](https://github.com/aa-parky/pipeworks_name_generation/commit/dc27bffd2ccc5c1b2da3e2d647142bb98fa833c5))
* Remove imported-members from autoapi to prevent duplicate warnings ([976cc36](https://github.com/aa-parky/pipeworks_name_generation/commit/976cc36253d092e917e7992123142b67c4a2b860))
* Resolve 3 CI test failures ([964c2d7](https://github.com/aa-parky/pipeworks_name_generation/commit/964c2d7d2f5f7da7eeea6ebf99b2337317cc4aae))
* Resolve Black formatting and mypy type errors in syllable extractor ([c3eb953](https://github.com/aa-parky/pipeworks_name_generation/commit/c3eb953ae2a7bf9bef961179802d13d65c5a91e1))
* Resolve markdownlint issues across documentation files ([56479a7](https://github.com/aa-parky/pipeworks_name_generation/commit/56479a7e81ac1ed306ce03069b40eb7811d6bbe3))
* Skip permission test on Windows (different permission model) ([6ddef3c](https://github.com/aa-parky/pipeworks_name_generation/commit/6ddef3c2845c65727f3f20cdc3d8b48a4338b737))
* Suppress expected Sphinx warnings for dataclass attributes and underscores ([495d5e3](https://github.com/aa-parky/pipeworks_name_generation/commit/495d5e3cd21fb444546bb265e5fac0d395ebd6c9))
* Use time.perf_counter() for higher precision timing on Windows ([8d32817](https://github.com/aa-parky/pipeworks_name_generation/commit/8d32817fcff22d9dd07cf4863b71aae0a90ec543))


### Documentation

* Add corpus_db to Claude Code documentation ([a261826](https://github.com/aa-parky/pipeworks_name_generation/commit/a2618269ecb7983e449b32ec99be5414d0ad45ba))
* Add corpus_db to README.md Build Tools section ([68912b1](https://github.com/aa-parky/pipeworks_name_generation/commit/68912b11701f48f7f39f6a4686afda9c608bffff))
* Add documentation content rules to CLAUDE.md ([23d9234](https://github.com/aa-parky/pipeworks_name_generation/commit/23d9234092e2fad821d77682deb9e78b6cf6a587))
* Add pre-commit hook for CLI documentation sync reminders ([4a064f3](https://github.com/aa-parky/pipeworks_name_generation/commit/4a064f3dec413ef3b01ad7b86033368dd1839087))
* Add table of contents and navigation links to README ([199e34b](https://github.com/aa-parky/pipeworks_name_generation/commit/199e34b27b6768ed9391affd4731f2e266894614))
* Automate CLI documentation with sphinx-argparse ([9a993e7](https://github.com/aa-parky/pipeworks_name_generation/commit/9a993e7bad5d5528089a5785ceb3aaf4e53db92a))
* **build_tools:** Add corpus_db to Sphinx documentation ([65faef7](https://github.com/aa-parky/pipeworks_name_generation/commit/65faef727b51dc55db0d466c7bc9f5d8d0c475d5))
* Complete Phase 7-8 of analysis refactoring with full documentation ([b70373d](https://github.com/aa-parky/pipeworks_name_generation/commit/b70373d7d23baa437ce8b50835927bb5f0ce5bfe))
* **pilot:** Refactor syllable_extractor to use auto-generated docs ([38fbfb2](https://github.com/aa-parky/pipeworks_name_generation/commit/38fbfb205f5b3f1f822778771b55ebdbc895eb3c))
* Refactor CLAUDE.md into modular documentation structure ([054ce99](https://github.com/aa-parky/pipeworks_name_generation/commit/054ce99b84ef061c16182384fcbaa1b3ae023389))
* Remove redundant API Reference section from analysis_tools.rst ([48fead8](https://github.com/aa-parky/pipeworks_name_generation/commit/48fead82c525bc74c933d67d98142416b4c8fc32))
* **rollout:** Complete auto-generated documentation refactor for all build tools ([97cdd8f](https://github.com/aa-parky/pipeworks_name_generation/commit/97cdd8f55feec3c392d3bf7bbae5edcfd5d1476c))
* Streamline README to focus on quick start and overview ([7bfad15](https://github.com/aa-parky/pipeworks_name_generation/commit/7bfad154cfd3c840b867a5a7083998ad311973a2))
* Update README with new syllable_extractor package usage ([3f06376](https://github.com/aa-parky/pipeworks_name_generation/commit/3f06376d2b4ffa4b2774227d5b7cdfd16659b13a))

## 0.2.1 (2026-01-08)


### Features

* Add batch processing CLI for syllable extractor ([1b6f1f8](https://github.com/aa-parky/pipeworks_name_generation/commit/1b6f1f85d8e576ee0891af506d278152a1cc2106))
* Add CLI support for automatic language detection ([60b1dd2](https://github.com/aa-parky/pipeworks_name_generation/commit/60b1dd20fe47b78e4bdbb4536412baba32bda0a4))
* Add comprehensive badges and codecov token to CI ([8cc155a](https://github.com/aa-parky/pipeworks_name_generation/commit/8cc155a77063f1cc5a2f1aaa7b4ce8586f5d7017))
* Add comprehensive CI/CD infrastructure and syllable extractor enhancements ([8487f9f](https://github.com/aa-parky/pipeworks_name_generation/commit/8487f9fedaeb522f755b91e7a0aad9546d0f4d1a))
* Add interactive HTML visualization to t-SNE visualizer ([8df6fa7](https://github.com/aa-parky/pipeworks_name_generation/commit/8df6fa739e97e362a1b02884fcc9eb23aa2e2b86))
* Add language code to output filenames for multi-language support ([ba1c3bf](https://github.com/aa-parky/pipeworks_name_generation/commit/ba1c3bfa34e633b9d28b33230c23e3b5c199d90a))
* Add optional language auto-detection for syllable extraction ([705261d](https://github.com/aa-parky/pipeworks_name_generation/commit/705261dfbd04cd39349c5d876a3318c2d0cad032))
* Add parameter logging and optional mapping to t-SNE visualizer ([f877d10](https://github.com/aa-parky/pipeworks_name_generation/commit/f877d106d660330b3b9bb9060639703888605b71))
* Add syllable walker for phonetic feature space exploration ([9d1b7e8](https://github.com/aa-parky/pipeworks_name_generation/commit/9d1b7e828dc322baf86e1e259e9541a9c230471f))
* Add t-SNE visualization tool for feature signature space ([5c8b44a](https://github.com/aa-parky/pipeworks_name_generation/commit/5c8b44a49b3e1603dcf48f7250a00d29e0af5bea))
* **build_tools:** Add corpus_db ledger for extraction run provenance ([53894ee](https://github.com/aa-parky/pipeworks_name_generation/commit/53894eefc4337d68f5c13e14152cf8e0cb6bc289))
* **build_tools:** Add syllable walker for phonetic space exploration ([058dec5](https://github.com/aa-parky/pipeworks_name_generation/commit/058dec5c6f5013b22ea56a083d1b965d8b6b8c76))
* **build_tools:** Integrate corpus_db into syllable_extractor CLI ([28c0ee9](https://github.com/aa-parky/pipeworks_name_generation/commit/28c0ee905cd6a0fef2f62aced92e2fe42f83d431))
* Complete Phase 1-4 of analysis refactoring - add dimensionality modules ([c8035e3](https://github.com/aa-parky/pipeworks_name_generation/commit/c8035e32648a7b843d452931bab64ad32c9cb276))
* Complete Phase 5-6 of analysis refactoring - add plotting modules and refactor tsne_visualizer ([d8d4097](https://github.com/aa-parky/pipeworks_name_generation/commit/d8d40976d09f20deedcd2c0205fe186aeea22585))
* Improve test coverage for syllable_extractor from 41% to 43% ([a149cb4](https://github.com/aa-parky/pipeworks_name_generation/commit/a149cb433c32e78de606169621fe056ea968342c))
* Make interactive t-SNE visualization responsive with min-width constraint ([9b8305a](https://github.com/aa-parky/pipeworks_name_generation/commit/9b8305a5c8d0bc684d4b57d1846339eef895014b))


### Bug Fixes

* Add missing sphinx-argparse dependency for ReadTheDocs ([a73bf2f](https://github.com/aa-parky/pipeworks_name_generation/commit/a73bf2f11983a548363e14a4255c87c2365f6aee))
* Clean up test_tsne_visualizer to keep only integration tests ([74b0cef](https://github.com/aa-parky/pipeworks_name_generation/commit/74b0cef315306309de54e33130f8ce98f4a24951))
* Configure matplotlib to use non-interactive backend for CI ([d7e0450](https://github.com/aa-parky/pipeworks_name_generation/commit/d7e04501aa249bfe81e90ad0fda9e43e9949729c))
* **corpus_db:** Store paths in POSIX format for cross-platform compatibility ([d4a19e5](https://github.com/aa-parky/pipeworks_name_generation/commit/d4a19e539eda03182479ccd1ae60976f5af28b25))
* **corpus_db:** Update test to use POSIX path format for comparison ([20c96f2](https://github.com/aa-parky/pipeworks_name_generation/commit/20c96f2b922fb4646f9d94c4aa59f896ddcc18a0))
* Create extractor instance after auto-detection for file saving ([3d5b13f](https://github.com/aa-parky/pipeworks_name_generation/commit/3d5b13f73bc0bb9c05d079a9588445553e9b4fce))
* **docs:** Link changelog.rst to auto-generated CHANGELOG.md ([dea252a](https://github.com/aa-parky/pipeworks_name_generation/commit/dea252a1e924f7ff7d05ceacb116881dfa4392f6))
* **docs:** Replace invalid JSON placeholder with valid example ([51e3b05](https://github.com/aa-parky/pipeworks_name_generation/commit/51e3b0529c5a754b563ea78d060e7137b76d151e))
* Expand mypy coverage to include tests and build_tools ([eb875c2](https://github.com/aa-parky/pipeworks_name_generation/commit/eb875c28829c74c252ff54a23e5259e409aefed4))
* Fix colorbar title overlapping with values in interactive t-SNE visualization ([4506aef](https://github.com/aa-parky/pipeworks_name_generation/commit/4506aefa2353e750dbd5fbb07e88a1ca53e6212c))
* Increase documentation warning threshold to accommodate dataclass warnings ([8d9657e](https://github.com/aa-parky/pipeworks_name_generation/commit/8d9657eb11a6ad1debe1916ce8e3f53e98f5998a))
* Make dimensionality modules optional and update CI dependencies ([c596a08](https://github.com/aa-parky/pipeworks_name_generation/commit/c596a08e502706d1719a3b21fba8fadc7100829c))
* Make pyphen import optional for documentation builds ([ecb33f1](https://github.com/aa-parky/pipeworks_name_generation/commit/ecb33f17cb155abeac5062d17246482339daf9b3))
* Make t-SNE visualizer dependencies optional for CI ([d14eac4](https://github.com/aa-parky/pipeworks_name_generation/commit/d14eac4e4d7d4c1855b5d3b65b6ce4bbac98624c))
* Remove _working/analysis_refactor.md from version control ([dc27bff](https://github.com/aa-parky/pipeworks_name_generation/commit/dc27bffd2ccc5c1b2da3e2d647142bb98fa833c5))
* Remove imported-members from autoapi to prevent duplicate warnings ([976cc36](https://github.com/aa-parky/pipeworks_name_generation/commit/976cc36253d092e917e7992123142b67c4a2b860))
* Resolve 3 CI test failures ([964c2d7](https://github.com/aa-parky/pipeworks_name_generation/commit/964c2d7d2f5f7da7eeea6ebf99b2337317cc4aae))
* Resolve Black formatting and mypy type errors in syllable extractor ([c3eb953](https://github.com/aa-parky/pipeworks_name_generation/commit/c3eb953ae2a7bf9bef961179802d13d65c5a91e1))
* Resolve markdownlint issues across documentation files ([56479a7](https://github.com/aa-parky/pipeworks_name_generation/commit/56479a7e81ac1ed306ce03069b40eb7811d6bbe3))
* Skip permission test on Windows (different permission model) ([6ddef3c](https://github.com/aa-parky/pipeworks_name_generation/commit/6ddef3c2845c65727f3f20cdc3d8b48a4338b737))
* Suppress expected Sphinx warnings for dataclass attributes and underscores ([495d5e3](https://github.com/aa-parky/pipeworks_name_generation/commit/495d5e3cd21fb444546bb265e5fac0d395ebd6c9))
* Use time.perf_counter() for higher precision timing on Windows ([8d32817](https://github.com/aa-parky/pipeworks_name_generation/commit/8d32817fcff22d9dd07cf4863b71aae0a90ec543))


### Documentation

* Add corpus_db to Claude Code documentation ([a261826](https://github.com/aa-parky/pipeworks_name_generation/commit/a2618269ecb7983e449b32ec99be5414d0ad45ba))
* Add corpus_db to README.md Build Tools section ([68912b1](https://github.com/aa-parky/pipeworks_name_generation/commit/68912b11701f48f7f39f6a4686afda9c608bffff))
* Add documentation content rules to CLAUDE.md ([23d9234](https://github.com/aa-parky/pipeworks_name_generation/commit/23d9234092e2fad821d77682deb9e78b6cf6a587))
* Add pre-commit hook for CLI documentation sync reminders ([4a064f3](https://github.com/aa-parky/pipeworks_name_generation/commit/4a064f3dec413ef3b01ad7b86033368dd1839087))
* Add table of contents and navigation links to README ([199e34b](https://github.com/aa-parky/pipeworks_name_generation/commit/199e34b27b6768ed9391affd4731f2e266894614))
* Automate CLI documentation with sphinx-argparse ([9a993e7](https://github.com/aa-parky/pipeworks_name_generation/commit/9a993e7bad5d5528089a5785ceb3aaf4e53db92a))
* **build_tools:** Add corpus_db to Sphinx documentation ([65faef7](https://github.com/aa-parky/pipeworks_name_generation/commit/65faef727b51dc55db0d466c7bc9f5d8d0c475d5))
* Complete Phase 7-8 of analysis refactoring with full documentation ([b70373d](https://github.com/aa-parky/pipeworks_name_generation/commit/b70373d7d23baa437ce8b50835927bb5f0ce5bfe))
* **pilot:** Refactor syllable_extractor to use auto-generated docs ([38fbfb2](https://github.com/aa-parky/pipeworks_name_generation/commit/38fbfb205f5b3f1f822778771b55ebdbc895eb3c))
* Refactor CLAUDE.md into modular documentation structure ([054ce99](https://github.com/aa-parky/pipeworks_name_generation/commit/054ce99b84ef061c16182384fcbaa1b3ae023389))
* Remove redundant API Reference section from analysis_tools.rst ([48fead8](https://github.com/aa-parky/pipeworks_name_generation/commit/48fead82c525bc74c933d67d98142416b4c8fc32))
* **rollout:** Complete auto-generated documentation refactor for all build tools ([97cdd8f](https://github.com/aa-parky/pipeworks_name_generation/commit/97cdd8f55feec3c392d3bf7bbae5edcfd5d1476c))
* Streamline README to focus on quick start and overview ([7bfad15](https://github.com/aa-parky/pipeworks_name_generation/commit/7bfad154cfd3c840b867a5a7083998ad311973a2))
* Update README with new syllable_extractor package usage ([3f06376](https://github.com/aa-parky/pipeworks_name_generation/commit/3f06376d2b4ffa4b2774227d5b7cdfd16659b13a))

## [0.2.0] - 2026-01-08

This release represents a significant expansion of the build tools infrastructure while maintaining the Phase 1
proof-of-concept generator. The focus has been on creating a robust corpus linguistics pipeline for syllable
extraction, normalization, feature annotation, and phonetic space analysis.

### Features

#### Build Tools Suite

- **Syllable Extractor**: Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
  - Support for 40+ languages
  - Automatic language detection with langdetect
  - Batch processing capabilities
  - Configurable syllable length constraints
  - Multi-language output file support

- **Syllable Normalizer**: 3-step normalization pipeline
  - Character decomposition and normalization
  - Phoneme-based normalization
  - Length and structure filtering

- **Syllable Feature Annotator**: Phonetic feature detection system
  - 12 phonetic feature detectors (consonant clusters, vowel patterns, etc.)
  - Binary feature signatures for each syllable
  - JSON output with metadata

- **Syllable Walker**: Phonetic space exploration tool
  - Navigate through similar syllables based on feature signatures
  - Step-by-step phonetic transformations
  - Interactive exploration of syllable relationships

#### Analysis Tools

- **Feature Signature Analysis**: Statistical analysis of annotated syllables
  - Feature frequency distributions
  - Correlation analysis
  - Comprehensive reporting

- **t-SNE Visualization**: Dimensionality reduction and visualization
  - Interactive HTML visualizations with plotly
  - Static matplotlib plots
  - Parameter logging and syllable mapping
  - Responsive design with min-width constraints
  - Optional dependencies for CI compatibility

- **Random Sampler**: Stratified random sampling of annotated syllables

### Documentation

- **Automated CLI Documentation**: Integration with sphinx-argparse for auto-generated command-line reference
- **Modular Documentation Structure**: Reorganized CLAUDE.md into topic-specific files in `claude/` directory
  - Architecture and Design
  - Development Guide
  - CI/CD Pipeline
  - Build Tools Documentation
- **Documentation Content Rules**: Single source of truth policy for docstrings vs RST files
- **Pre-commit Hook**: Reminders for CLI documentation synchronization

### Internal Changes

- **Analysis Tools Reorganization**: Moved to top-level `build_tools/syllable_analysis/` structure
- **Syllable Extractor Modularization**: Extracted into proper package structure
- **CI Improvements**: Optional dependencies handling for matplotlib and dimensionality modules
- **Test Coverage Improvements**: Expanded coverage across build tools

### Fixes

- Platform compatibility fixes (Windows permission handling, matplotlib backend configuration)
- Sphinx documentation warnings resolution
- ReadTheDocs build improvements (optional pyphen import, dependency handling)
- Interactive visualization improvements (colorbar overlap fix, responsive design)
- Test suite cleanup and CI stability improvements

## [0.1.0] - Initial Release

Initial proof-of-concept release with Phase 1 generator:

- Basic `NameGenerator` class with deterministic seeding
- "simple" pattern with hardcoded syllables
- Zero runtime dependencies
- Comprehensive CI/CD infrastructure (GitHub Actions, pre-commit hooks)
- Sphinx documentation with ReadTheDocs integration
- GPL-3.0-or-later license
