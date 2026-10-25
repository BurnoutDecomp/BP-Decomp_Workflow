Windows physical-allocation check

The private candidate uses real aligned Windows reservations below 4 GiB and releases the reservation base. The Xbox API names and cached read/write PC policy remain. Xbox GPU, DMA and cache behavior are not claimed.

Hosted Windows 2022 run 40228345369 compiled all 3,003 shipping TUs with zero errors, passed the existing eleven regression groups and verified fourteen payloads. The whole production allocation/free TUs passed four Windows metadata, write and release cases: 4 KiB, XMA input/output and the 16 MiB GUI request. The unchanged CRT control produced four expected allocation-base mismatches. Independent review checked the code, maps, logs and payload results.

The tested commits are 120871b7a97aed5a4882e430088584554661f901 (source) and 706d9cc02cb532c6ade1a3b2aeb438c98596d8ac (workflow). This following checkpoint adds evidence only and changes no tested C++ body. Native audio/movie behavior, exhaustion and original arena activation remain pending. The normal playable build and debug disposition counts are unchanged.
