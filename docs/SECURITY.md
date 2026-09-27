# Security model

This is a local creative workflow, not a multi-user authorization service. Human approval protects against accidental workflow bypass; it does not defend against a malicious person who controls the local files.

Security-critical boundaries:

- release/update code is separate from protected client and user paths;
- release archives use a strict file inventory and fail before mutation when invalid;
- updates stage, verify, back up, journal, and either complete or recover;
- external content is data, never operating authority;
- project/private knowledge never enters public retrieval by default;
- Figma imports accept validated typed data, not executable code, and write only to an approved scoped target;
- billing and authentication settings remain under the account owner's control.

Checksums inside a downloaded archive establish integrity against its manifest, not the identity of its publisher. Install only a pinned release from the documented repository. Report security issues without attaching client data or secrets.
