# Reading your C feature from JavaScript

The package includes the existing `Pedal` JavaScript API and its local module
closure. There is no npm dependency or bundled catalog/firmware binary. Use an
ES module in a browser with native Web MIDI and SysEx support, served from a
secure context. Connect only after installation is complete and Suite is closed.

```js
import {Pedal, connectWebMidi} from './web/gp50/pedal.mjs';
const {transport} = await connectWebMidi();
const pedal = new Pedal(transport);
try {
  const identity = await pedal.identity();
  // The example's manifest owns 0x77 and returns schema 1, then one answer byte.
  const payload = await pedal.readComponent(identity, 0x77, {schema: 1, length: 2});
  console.log(payload[1]); // 42, or the value you compiled into answer_main.c
} finally {
  transport.close();
}
```

The manifest's GET selector `0x77` corresponds to logical message `12 77`; its
reply is `12 77 01 <answer>`. The API handles packet framing and serialization.
`length` includes the schema byte. The answer starter has no SET callback, so
writes are refused. A different component with a SET callback uses
`pedal.writeComponent(identity, selector, Uint8Array.of(...))`; payload length
must match its manifest declaration.

The API checks capability bit 8, schema and exact reply length. Component requests
are serialized and stop after a refusal, bad reply or timeout. Inspect the cause
before opening a fresh connection; do not continue sending from a halted instance.
A missing identity reply returns `null` and the component read then refuses before
sending; it does not establish that your feature is installed.

From the package root, Node can run the included fake-transport tests:

```sh
node web/test/test_components.mjs
```

These test host validation, serialization and failure handling, not MIDI timing
or behaviour on a pedal. Our features are read the same way, e.g. the CPU load:
`pedal.cpuLoad(identity)` (`12 7a`).

Third-party notice: `web/THIRD_PARTY.md`. Installing and recovery:
`sdk/INSTALL_AND_RECOVER.md`.
