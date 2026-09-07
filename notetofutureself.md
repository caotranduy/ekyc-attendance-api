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

---

# Conda Environment Setup & Dependency Installation

## 1. Prerequisites
- **Conda:** Miniconda or Anaconda installed.
- **Python Version:** **Python 3.10** strictly.
  > [!IMPORTANT]
  > Python 3.10 is required. Newer Python versions (3.11+) often fail when compiling or linking native C++ extensions for `dlib` and `faiss-cpu` on Windows.
- **C++ Compiler (Windows):** Visual Studio C++ Build Tools or CMake via conda-forge.

---

## 2. Step-by-Step Conda Setup

### Step 1: Create and Activate Conda Environment
Open terminal (Anaconda Prompt or PowerShell) at the project root:

```bash
# 1. Create a clean Conda environment with Python 3.10
conda create -n face_checkin python=3.10 -y

# 2. Activate the environment
conda activate face_checkin
```

### Step 2: Install Build Tools & Dlib
To prevent native C++ compilation errors on Windows, install `cmake` and prebuilt `dlib` via `conda-forge`:

```bash
# Install CMake
conda install -c conda-forge cmake -y

# Install precompiled Dlib for Python 3.10
conda install -c conda-forge dlib -y
```
*(Note: If building Dlib with GPU CUDA and cuDNN support, follow the CMake instructions at the top of this file).*

### Step 3: Install All Remaining Dependencies
Install the required framework, database, and AI packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```