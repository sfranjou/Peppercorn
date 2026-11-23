# Stock compatibility facts

`v110_code_ownership.json.zlib` replaces full decompiler exports in the author
package's placement and code-hole checks. It records instruction address/length
pairs, direct references and function-body ranges for the exact decoded V1.1.0 B
region. No instruction text or pseudocode is needed by the builder. The loader
pins both the compressed map and the decoded stock B hashes and refuses mismatches.

It contains addresses, lengths and branch targets only: no instruction bytes or code.
