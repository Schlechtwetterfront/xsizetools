C++ Source
===

This is the C++ source for the CGeoAccessorWrappers.xx.dlls. Note that 32 builds use a different SDK and environment than the 64 builds.

If you want to build with an older XSI SDK version (like 7.5) with a newer Visual Studio version then you will need to adjust
the make files that come with the XSI SDK. I've found that just copying the ´´mkfiles´´ folder from a newer SDK and replacing the
old one with that works just fine.