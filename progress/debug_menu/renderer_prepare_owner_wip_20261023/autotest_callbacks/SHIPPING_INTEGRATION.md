# Shipping source availability

The executable authority is `tools/build/build_game_exe.bat` plus `compile_exe.py`, not CMake. This packet inspected exact parent `49b019071a13b1e59d243e05b4a90fa76664223e` and the existing hosted artifact for source `e8e4918bae6f71736a191ca17a900f9212e52630`.

The batch source list has 3021 explicit source entries and 3002 unique paths. This exactly matches hosted build.log's 3002 TUs. compile_exe.py::parse_sources consumes quoted source-path lines from build.rsp and deduplicates them; it does not discover arbitrary src/*.cpp files. No source includes the AutoTest/helper .cpp files as a unity bridge. The exact hosted map contains no AutoTestManager/LUACallbackHelper symbols. The latest hosted log is incremental (4 compiled, 2998 reused), so absence from that log alone would not prove a file is unmounted.

The exact parsed shipping list has no BrnAutoTestManager.cpp, BrnAutoTestManagerLUACallbacks.cpp, or BrnLUACallbackHelper.cpp. These facts are frozen under `evidence/shipping/`, including the original batch/driver, generated read-only source enumeration, hosted build.log, and provenance. The older local build.rsp has 2994 entries and is not the exact hosted candidate list; it was not used to infer the current hosted count.

When Root deliberately composes the WIP owner and this callback proposal, the executable source list needs the canonical BrnAutoTestManager.cpp and BrnLUACallbackHelper.cpp TUs. Do not mount the deleted legacy callback file as well. No active mount change is supplied or performed here. CMake availability does not establish executable availability.

The seven callback bodies and helper methods are now source recovered in this proposal. Link/runtime availability remains unverified. The original four-argument GameData Prepare core and native renderer allocation/sky-dome integration remain separate blockers; this does not make the five-stack owner activation ready.
