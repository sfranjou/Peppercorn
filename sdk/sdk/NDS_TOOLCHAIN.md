# NDS32 feature compiler setup

The feature SDK uses a freestanding `nds32le-elf` C compiler and binutils. The
compiler is an external input, supplied by the SDK user. It is separate from the
ARM Clang/binutils used for audio effects. These instructions record the macOS
setup used by the project; a fresh installation has not been rerun for this guide.

The qualified versions are GCC 16.2.0 and GNU binutils 2.47. The initial build used
Apple Silicon macOS, Apple command-line developer tools, GNU make and Homebrew's
`gmp`, `mpfr`, `libmpc` and `isl` under `/opt/homebrew`. Install those prerequisites
using your normal package manager. Other hosts and compiler versions need their
own qualification; matching a version number alone does not establish identical
compiler output.

Obtain the two source archives from GNU, keeping their source licenses and notices:

| Source | SHA-256 |
| --- | --- |
| [binutils-2.47.tar.xz](https://ftp.gnu.org/gnu/binutils/binutils-2.47.tar.xz) | `154ab23b60070e8f27013c22977f1129425d67d1e8acd6e13010e617811e4cff` |
| [gcc-16.2.0.tar.xz](https://ftp.gnu.org/gnu/gcc/gcc-16.2.0/gcc-16.2.0.tar.xz) | `e6738e29597f733270731aa90600f37ffdc045079dfc27ec7e8192cc81085c3e` |

Check the downloaded archives with `shasum -a 256` before extracting them. The
project's original downloads also passed GNU detached-signature verification
with the GNU keyring. No compiler binaries or GNU sources are included in the
starter ARM package.

Choose a writable folder for the compiler. Extract the archives into its `src/`
subdirectory, producing `src/binutils-2.47` and `src/gcc-16.2.0`. The following
commands build into a local `prefix/`, without a system-wide compiler install:

```sh
export GP50_NDS_BUILD=/absolute/path/to/nds32-toolchain
export GP50_NDS_DEPS=/opt/homebrew
export GP50_NDS_JOBS=8
mkdir -p "$GP50_NDS_BUILD/build-binutils" "$GP50_NDS_BUILD/build-gcc"
export PATH="$GP50_NDS_BUILD/prefix/bin:$PATH"
cd "$GP50_NDS_BUILD/build-binutils"
../src/binutils-2.47/configure --target=nds32le-elf \
  --prefix="$GP50_NDS_BUILD/prefix" --disable-nls --disable-werror \
  --disable-gdb --disable-sim --disable-gprofng
make -j"$GP50_NDS_JOBS"
make install
cd "$GP50_NDS_BUILD/build-gcc"
../src/gcc-16.2.0/configure --target=nds32le-elf \
  --prefix="$GP50_NDS_BUILD/prefix" --disable-nls --enable-languages=c \
  --without-headers --disable-shared --disable-threads --disable-libssp \
  --disable-libquadmath --disable-libgomp --disable-multilib \
  --with-gmp="$GP50_NDS_DEPS" --with-mpfr="$GP50_NDS_DEPS" \
  --with-mpc="$GP50_NDS_DEPS" --with-isl="$GP50_NDS_DEPS"
make -j"$GP50_NDS_JOBS" all-gcc
make install-gcc
make -j"$GP50_NDS_JOBS" all-target-libgcc
make install-target-libgcc
"$GP50_NDS_BUILD/prefix/bin/nds32le-elf-gcc" -dumpmachine
"$GP50_NDS_BUILD/prefix/bin/nds32le-elf-gcc" -dumpfullversion
"$GP50_NDS_BUILD/prefix/bin/nds32le-elf-ld" --version
```

Expected target: `nds32le-elf`; GCC version: `16.2.0`; binutils version: `2.47`.
The isolated feature composer accepts the resulting prefix through
`--toolchain-prefix /absolute/path/to/nds32-toolchain/prefix`.

Let the SDK builder select ISA, ABI, float convention and linker flags. Feature
source needs no toolchain-path, linker-address or register-allocation edits.
In particular, stock floating-point calls require the builder's selected hard-float
convention. The SDK's per-image checks bind compiled objects and imports to the
image; this setup recipe does not replace those checks or prove hardware behavior.
