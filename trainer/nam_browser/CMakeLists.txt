cmake_minimum_required(VERSION 3.20)
project(ToneBrowserRawNAM LANGUAGES CXX)
if(NOT DEFINED NAM_CORE)
 message(FATAL_ERROR "Set NAM_CORE to the pinned source directory")
endif()
file(GLOB_RECURSE CORE_SOURCES "${NAM_CORE}/NAM/*.cpp")
add_executable(teacher teacher.cpp ${CORE_SOURCES})
target_include_directories(teacher PRIVATE "${NAM_CORE}" "${NAM_CORE}/Dependencies/eigen" "${NAM_CORE}/Dependencies/nlohmann")
target_compile_features(teacher PRIVATE cxx_std_20)
target_compile_definitions(teacher PRIVATE NAM_SAMPLE_FLOAT EIGEN_STACK_ALLOCATION_LIMIT=0 NAM_USE_INLINE_GEMM)
target_compile_options(teacher PRIVATE -O3 -msimd128 -fwasm-exceptions)
target_link_options(teacher PRIVATE -O3 -fwasm-exceptions --no-entry
 -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createTeacher -sENVIRONMENT=web,worker,node
 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=64MB -sMAXIMUM_MEMORY=512MB -sSTACK_SIZE=4MB
 -sINCOMING_MODULE_JS_API=wasmBinary,locateFile,print,printErr
 -sEXPORTED_FUNCTIONS=_malloc,_free
 -sEXPORTED_RUNTIME_METHODS=stringToUTF8,lengthBytesUTF8,UTF8ToString,HEAPF32,HEAPU8
 -sFILESYSTEM=0 -sDYNAMIC_EXECUTION=0)
