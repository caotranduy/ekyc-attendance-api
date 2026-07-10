due to Python's faulty directory detection, setuptool cannot find the path to cuDNN library
best solution I did is pasting this block of cmake instruction
```cmake
set(DLIB_USE_CUDA ON CACHE BOOL "" FORCE)
set(CUDNN_INCLUDE_PATH "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.4/include" CACHE PATH "" FORCE)
set(CUDNN_LIBRARY_PATH "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.4/lib/x64/cudnn.lib" CACHE FILEPATH "" FORCE)
```

to line 11 under ``project(dlib_python_bindings)`` in 
``dlib/tools/python/CMakeLists.txt``, then run 
``python setup.py install``