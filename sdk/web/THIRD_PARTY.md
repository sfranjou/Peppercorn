# Third-party notices

`gp50/prst.mjs` adapts `app/static/prst.js` from
[drewmerc302/valeton-gp50](https://github.com/drewmerc302/valeton-gp50), vendored commit `aadcf9b`.
`gp50/presets.mjs` uses its documented preset-write payload and validation approach.
The editor adopts the Explorer workflow (presets, chain, block detail, capture bank); its UI is newly written.
The captured factory blank is omitted from this port. No firmware or factory audio is bundled.

MIT License

Copyright (c) 2026 Andrew Mercurio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

The SDK includes these JavaScript modules for host control (not the browser DSP assets or their toolchain).
Project-authored SDK code is MIT licensed (`LICENSE`).

## Audio effects

- **Cloud Verb** (`sdk/effects/clouds_verb/`): port of the Mutable Instruments Clouds reverb
  (`clouds/dsp/fx/reverb.h`), Copyright 2014 Emilie Gillet, MIT license (full notice in the source file).
- **Tape** (`sdk/effects/tape/`): approach after Airwindows ToTape8 (MIT, airwindows.com); code written for this
  project.
- **FDN Verb** (`sdk/effects/fdn_verb/`): written for this project from published papers (Stautner & Puckette
  1982; Jot & Chaigne 1991).
